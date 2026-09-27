from PyQt6.QtCore import QPoint, QPropertyAnimation, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt6.QtWidgets import QLabel


def _paint_atom(p: QPainter, S: int):
    """원자 오비탈 아이콘 — 대시보드 FAB 디자인과 동일."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx = cy = S / 2.0
    margin = S * 0.04

    # 배경 원 (dark navy)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#0e1c40"))
    p.drawEllipse(QRectF(margin, margin, S - 2 * margin, S - 2 * margin))

    # 오비탈 타원 3개 (0°, 60°, 120°)
    rx = S * 0.33
    ry = S * 0.115

    pen = QPen(QColor("#4a9eff"), max(1.0, S * 0.022))
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    for angle in (0, 60, 120):
        p.save()
        p.translate(cx, cy)
        p.rotate(angle)
        p.drawEllipse(QRectF(-rx, -ry, rx * 2, ry * 2))
        p.restore()

    # 핵 — 파란 원 + 흰 중심점
    p.setPen(Qt.PenStyle.NoPen)
    nr = S * 0.072
    p.setBrush(QColor("#4a9eff"))
    p.drawEllipse(QRectF(cx - nr, cy - nr, nr * 2, nr * 2))

    cr = S * 0.034
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QRectF(cx - cr, cy - cr, cr * 2, cr * 2))


class _PopupBubble(QLabel):
    """아이콘 위에 떠오르는 말풍선 팝업."""

    W, H = 148, 36
    TAIL  = 8   # 꼬리 높이

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H + self.TAIL)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(180)

    def show_popup(self):
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._opacity_effect.opacity())
        self._anim.setEndValue(1.0)
        self._anim.start()

    def hide_popup(self):
        self._anim.stop()
        self._anim.setStartValue(self._opacity_effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._on_hide_done)
        self._anim.start()

    def _on_hide_done(self):
        try:
            self._anim.finished.disconnect(self._on_hide_done)
        except RuntimeError:
            pass
        if self._opacity_effect.opacity() < 0.05:
            self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H, T = self.W, self.H, self.TAIL

        # 그림자
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 30))
        shadow = QPainterPath()
        shadow.addRoundedRect(QRectF(2, 2, W - 2, H), 10, 10)
        p.drawPath(shadow)

        # 말풍선 몸통
        p.setBrush(QColor(72, 105, 245))
        body = QPainterPath()
        body.addRoundedRect(QRectF(0, 0, W - 2, H), 10, 10)
        p.drawPath(body)

        # 꼬리 (아래쪽 가운데)
        tail = QPainterPath()
        cx = (W - 2) / 2
        tail.moveTo(cx - 7, H)
        tail.lineTo(cx,     H + T)
        tail.lineTo(cx + 7, H)
        tail.closeSubpath()
        p.drawPath(tail)

        # 텍스트
        p.setPen(QColor(255, 255, 255))
        font = QFont("Malgun Gothic", 9)
        font.setWeight(QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(0, 0, W - 2, H), Qt.AlignmentFlag.AlignCenter, "무엇이든 물어보세요 💬")


class RobotAvatarWidget(QLabel):
    """헤더용 소형 원자 오비탈 아바타."""

    def __init__(self, size: int = 36, parent=None):
        super().__init__(parent)
        self._sz = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        _paint_atom(QPainter(self), self._sz)


def _paint_robot(p: QPainter, S: int):
    """로봇 아이콘 공통 페인트 함수 (레거시 — 미사용)."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    cx = S / 2

    bg = QRadialGradient(cx - S * 0.08, S * 0.19, S * 0.8)
    bg.setColorAt(0, QColor(110, 130, 200))
    bg.setColorAt(1, QColor(50, 65, 140))
    p.setBrush(bg)
    p.drawEllipse(QRectF(S * 0.04, S * 0.04, S * 0.92, S * 0.92))

    sc = S / 52.0

    def r(x, y, w, h): return QRectF(cx + (x - 26) * sc, y * sc, w * sc, h * sc)

    body_grad = QRadialGradient(cx, 35 * sc, 14 * sc)
    body_grad.setColorAt(0, QColor(240, 244, 255))
    body_grad.setColorAt(1, QColor(190, 200, 230))
    p.setBrush(body_grad)
    p.drawRoundedRect(r(-7, 33, 14, 12), 6 * sc, 6 * sc)

    p.setBrush(QColor(200, 210, 235))
    p.drawRoundedRect(r(-14, 34, 6, 9), 3 * sc, 3 * sc)
    p.drawRoundedRect(r(8, 34, 6, 9), 3 * sc, 3 * sc)

    head_r = 11 * sc
    hcx, hcy = cx, 22 * sc
    hg = QRadialGradient(hcx - 3 * sc, hcy - 4 * sc, head_r * 1.6)
    hg.setColorAt(0, QColor(250, 252, 255))
    hg.setColorAt(0.7, QColor(220, 228, 248))
    hg.setColorAt(1, QColor(170, 185, 225))
    p.setBrush(hg)
    p.drawEllipse(QRectF(hcx - head_r, hcy - head_r, head_r * 2, head_r * 2))

    p.setBrush(QColor(190, 200, 230))
    p.drawRoundedRect(QRectF(hcx - head_r - 3 * sc, hcy - 4 * sc, 4 * sc, 8 * sc), 2 * sc, 2 * sc)
    p.drawRoundedRect(QRectF(hcx + head_r - 1 * sc, hcy - 4 * sc, 4 * sc, 8 * sc), 2 * sc, 2 * sc)

    p.setPen(QPen(QColor(180, 195, 230), 1.5 * sc))
    p.drawLine(QRectF(hcx - 4 * sc, hcy - head_r, 0, 0).topLeft(),
               QRectF(hcx - 6 * sc, hcy - head_r - 7 * sc, 0, 0).topLeft())
    p.drawLine(QRectF(hcx + 4 * sc, hcy - head_r, 0, 0).topLeft(),
               QRectF(hcx + 6 * sc, hcy - head_r - 7 * sc, 0, 0).topLeft())
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(140, 200, 255))
    p.drawEllipse(QRectF(hcx - 8.5 * sc, hcy - head_r - 10 * sc, 5 * sc, 5 * sc))
    p.drawEllipse(QRectF(hcx + 3.5 * sc, hcy - head_r - 10 * sc, 5 * sc, 5 * sc))

    p.setBrush(QColor(18, 22, 48))
    p.drawRoundedRect(QRectF(hcx - 8 * sc, hcy - 3 * sc, 16 * sc, 10 * sc), 4 * sc, 4 * sc)

    for ex in [hcx - 4.5 * sc, hcx + 4.5 * sc]:
        ey = hcy + 2.5 * sc
        glow = QRadialGradient(ex, ey, 5 * sc)
        glow.setColorAt(0, QColor(0, 230, 255, 220))
        glow.setColorAt(1, QColor(0, 120, 200, 0))
        p.setBrush(glow)
        p.drawEllipse(QRectF(ex - 5 * sc, ey - 5 * sc, 10 * sc, 10 * sc))
        p.setBrush(QColor(80, 220, 255))
        p.drawEllipse(QRectF(ex - 3 * sc, ey - 3 * sc, 6 * sc, 6 * sc))
        p.setBrush(QColor(200, 245, 255))
        p.drawEllipse(QRectF(ex - 1.2 * sc, ey - 1.8 * sc, 2.4 * sc, 2.4 * sc))

    base = QRadialGradient(cx, S - 6 * sc, 10 * sc)
    base.setColorAt(0, QColor(80, 160, 255, 180))
    base.setColorAt(1, QColor(40, 100, 220, 0))
    p.setBrush(base)
    p.drawEllipse(QRectF(cx - 10 * sc, S - 14 * sc, 20 * sc, 10 * sc))


class FloatingChatbotIcon(QLabel):
    """드래그 가능한 반투명 챗봇 아이콘 — 호버 시 말풍선 팝업, 클릭 시 채팅창 토글."""

    clicked = pyqtSignal()
    SIZE = 52
    _OPACITY_DIM    = 0.75
    _OPACITY_BRIGHT = 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("AI 문의")
        self._drag_pos: QPoint | None = None
        self._opacity = self._OPACITY_DIM
        self._bounds_window = None  # 경계 기준이 되는 메인 윈도우

    def set_bounds_window(self, window):
        """드래그 경계를 이 윈도우의 frameGeometry로 제한한다."""
        self._bounds_window = window

    # ── 아이콘 그리기 ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setOpacity(self._opacity)
        _paint_atom(p, self.SIZE)
        return
        S = self.SIZE
        cx = S / 2

        # ── 배경 원 ──────────────────────────────────────────────────────────
        bg = QRadialGradient(cx - 4, 10, S * 0.8)
        bg.setColorAt(0, QColor(110, 130, 200))
        bg.setColorAt(1, QColor(50, 65, 140))
        p.setBrush(bg)
        p.drawEllipse(QRectF(2, 2, S - 4, S - 4))

        # ── 몸통 (흰 캡슐) ───────────────────────────────────────────────────
        body_w, body_h = 14, 12
        body_x = cx - body_w / 2
        body_y = 33
        body_grad = QRadialGradient(cx, body_y + 4, body_w)
        body_grad.setColorAt(0, QColor(240, 244, 255))
        body_grad.setColorAt(1, QColor(190, 200, 230))
        p.setBrush(body_grad)
        p.drawRoundedRect(QRectF(body_x, body_y, body_w, body_h), 6, 6)

        # ── 팔 ──────────────────────────────────────────────────────────────
        arm_col = QColor(200, 210, 235)
        p.setBrush(arm_col)
        p.drawRoundedRect(QRectF(body_x - 7, body_y + 1, 6, 9), 3, 3)   # 왼팔
        p.drawRoundedRect(QRectF(body_x + body_w + 1, body_y + 1, 6, 9), 3, 3)  # 오른팔

        # ── 머리 (흰 구체) ───────────────────────────────────────────────────
        head_r = 11.0
        head_cx, head_cy = cx, 22.0
        head_grad = QRadialGradient(head_cx - 3, head_cy - 4, head_r * 1.6)
        head_grad.setColorAt(0, QColor(250, 252, 255))
        head_grad.setColorAt(0.7, QColor(220, 228, 248))
        head_grad.setColorAt(1, QColor(170, 185, 225))
        p.setBrush(head_grad)
        p.drawEllipse(QRectF(head_cx - head_r, head_cy - head_r, head_r * 2, head_r * 2))

        # ── 귀/사이드 패널 ───────────────────────────────────────────────────
        p.setBrush(QColor(190, 200, 230))
        p.drawRoundedRect(QRectF(head_cx - head_r - 3, head_cy - 4, 4, 8), 2, 2)
        p.drawRoundedRect(QRectF(head_cx + head_r - 1, head_cy - 4, 4, 8), 2, 2)

        # ── 안테나 ───────────────────────────────────────────────────────────
        p.setPen(QPen(QColor(180, 195, 230), 1.5))
        p.drawLine(QRectF(head_cx - 4, head_cy - head_r, 0, 0).topLeft(),
                   QRectF(head_cx - 6, head_cy - head_r - 7, 0, 0).topLeft())
        p.drawLine(QRectF(head_cx + 4, head_cy - head_r, 0, 0).topLeft(),
                   QRectF(head_cx + 6, head_cy - head_r - 7, 0, 0).topLeft())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(140, 200, 255))
        p.drawEllipse(QRectF(head_cx - 8.5, head_cy - head_r - 10, 5, 5))
        p.drawEllipse(QRectF(head_cx + 3.5, head_cy - head_r - 10, 5, 5))

        # ── 얼굴 바이저 (어두운 면판) ────────────────────────────────────────
        visor_w, visor_h = 16, 10
        visor_x = head_cx - visor_w / 2
        visor_y = head_cy - 3
        p.setBrush(QColor(18, 22, 48))
        p.drawRoundedRect(QRectF(visor_x, visor_y, visor_w, visor_h), 4, 4)

        # ── 눈 (청록 발광) ───────────────────────────────────────────────────
        for ex in [head_cx - 4.5, head_cx + 4.5]:
            ey = head_cy + 2.5
            glow = QRadialGradient(ex, ey, 5)
            glow.setColorAt(0, QColor(0, 230, 255, 220))
            glow.setColorAt(1, QColor(0, 120, 200, 0))
            p.setBrush(glow)
            p.drawEllipse(QRectF(ex - 5, ey - 5, 10, 10))
            p.setBrush(QColor(80, 220, 255))
            p.drawEllipse(QRectF(ex - 3, ey - 3, 6, 6))
            p.setBrush(QColor(200, 245, 255))
            p.drawEllipse(QRectF(ex - 1.2, ey - 1.8, 2.4, 2.4))

        # ── 하단 파란 글로우 ─────────────────────────────────────────────────
        base = QRadialGradient(cx, S - 6, 10)
        base.setColorAt(0, QColor(80, 160, 255, 180))
        base.setColorAt(1, QColor(40, 100, 220, 0))
        p.setBrush(base)
        p.drawEllipse(QRectF(cx - 10, S - 14, 20, 10))

    # ── 호버 ──────────────────────────────────────────────────────────────────

    def _set_opacity(self, value: float):
        self._opacity = value
        self.update()

    def enterEvent(self, event):
        self._set_opacity(self._OPACITY_BRIGHT)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._drag_pos is None:
            self._set_opacity(self._OPACITY_DIM)
        super().leaveEvent(event)

    # ── 드래그 ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._did_drag = False
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            if self._bounds_window is not None:
                geo = self._bounds_window.frameGeometry()
                pad = 8
                new_pos.setX(max(geo.left() + pad, min(new_pos.x(), geo.right()  - self.width()  - pad)))
                new_pos.setY(max(geo.top()  + pad, min(new_pos.y(), geo.bottom() - self.height() - pad)))
            if (new_pos - self.pos()).manhattanLength() > 4:
                self._did_drag = True
            self.move(new_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        dragged = getattr(self, "_did_drag", False)
        self._drag_pos = None
        self._did_drag = False
        if not self.underMouse():
            self._set_opacity(self._OPACITY_DIM)
        if not dragged:
            self.clicked.emit()
        event.accept()

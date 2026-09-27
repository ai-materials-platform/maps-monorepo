from PyQt6.QtCore import Qt, QTimer, QEvent, QPoint, QRect, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class PredictionGuideOverlay(QWidget):
    """물성 예측 페이지 위에 떠 있는 단계별 가이드 오버레이."""

    NAV_H = 64

    def __init__(self, steps, parent=None, toolbar_h=0):
        super().__init__(parent)
        self._steps = steps
        self._step = 0
        self._toolbar_h = toolbar_h
        if parent:
            self.setGeometry(0, toolbar_h, parent.width(), parent.height() - toolbar_h)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._bubble = QLabel(self)
        self._bubble.setWordWrap(True)
        self._bubble.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._bubble.setStyleSheet(
            "background: #FFFFFF; color: #1E293B; border: 2px solid #1E293B; "
            "border-radius: 12px; padding: 14px 16px; font-size: 12px;"
        )
        self._bubble.setFixedSize(280, 210)

        self._nav = QWidget(self)
        self._nav.setStyleSheet("background: #1E293B; border-bottom: 1px solid #334155;")
        nav_layout = QHBoxLayout(self._nav)
        nav_layout.setContentsMargins(24, 0, 24, 0)
        nav_layout.setSpacing(10)

        btn_base = (
            "QPushButton {{ background: {bg}; color: white; border: none; border-radius: 14px; "
            "font-weight: 700; font-size: 12px; min-width: 80px; min-height: 34px; padding: 0 16px; }}"
            "QPushButton:hover {{ background: {hv}; }}"
            "QPushButton:disabled {{ background: #475569; color: #94A3B8; }}"
        )
        self._prev_btn = QPushButton("◀  이전")
        self._prev_btn.setStyleSheet(btn_base.format(bg="#475569", hv="#64748B"))
        self._prev_btn.clicked.connect(self._go_prev)

        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_label.setStyleSheet("color: #CBD5E1; font-size: 13px; font-weight: 700;")

        self._next_btn = QPushButton("다음  ▶")
        self._next_btn.setStyleSheet(btn_base.format(bg="#1E293B", hv="#334155"))
        self._next_btn.clicked.connect(self._go_next)

        self._close_btn = QPushButton("✕  닫기")
        self._close_btn.setStyleSheet(btn_base.format(bg="#DC2626", hv="#EF4444"))
        self._close_btn.clicked.connect(self.close)

        nav_layout.addWidget(self._prev_btn)
        nav_layout.addStretch(1)
        nav_layout.addWidget(self._step_label)
        nav_layout.addStretch(1)
        nav_layout.addWidget(self._next_btn)
        nav_layout.addSpacing(12)
        nav_layout.addWidget(self._close_btn)

        self._update_step()

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            self.parent().installEventFilter(self)
        self._relayout()
        self._position_bubble()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._go_prev()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Space):
            self._go_next()
        elif key == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.parent():
            self.parent().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            th = self._toolbar_h
            self.setGeometry(0, th, obj.width(), obj.height() - th)
            self._relayout()
            self._position_bubble()
        return False

    def _relayout(self):
        self._nav.setGeometry(0, 0, self.width(), self.NAV_H)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()
        self._position_bubble()

    def _spotlight_rect(self):
        if self._step >= len(self._steps):
            return None
        w = self._steps[self._step].get("widget")
        if not w or not w.isVisible():
            return None
        try:
            global_pos = w.mapToGlobal(QPoint(0, 0))
            local_pos = self.mapFromGlobal(global_pos)
            return QRect(local_pos, w.size()).adjusted(-10, -10, 10, 10)
        except Exception:
            return None

    def _update_step(self):
        total = len(self._steps)
        self._step_label.setText(f"{self._step + 1}  /  {total}")
        self._prev_btn.setEnabled(self._step > 0)
        self._next_btn.setEnabled(self._step < total - 1)
        step = self._steps[self._step]
        self._bubble.setText(step["text"])
        if step.get("on_show"):
            step["on_show"]()
        self.update()
        QTimer.singleShot(30, self._position_bubble)

    def _position_bubble(self):
        if self._step >= len(self._steps):
            return
        bubble_w = self._bubble.width()
        bubble_h = self._bubble.height()

        spot = self._spotlight_rect()
        content_top = self.NAV_H + 12
        content_bottom = self.height() - 12
        usable_h = content_bottom - content_top

        if spot:
            bx = spot.right() + 18
            by = spot.top()
            if bx + bubble_w > self.width() - 8:
                bx = spot.left() - bubble_w - 18
            if bx < 8:
                bx = max(8, (self.width() - bubble_w) // 2)
                by = spot.bottom() + 16
            by = max(content_top, min(by, content_bottom - bubble_h))
        else:
            bx = (self.width() - bubble_w) // 2
            by = content_top + (usable_h - bubble_h) // 2
        self._bubble.move(bx, by)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ov = QColor(0, 0, 0, 170)
        r = self.rect()
        content_top = self.NAV_H

        spot = self._spotlight_rect()
        if spot:
            painter.fillRect(QRect(r.left(), content_top, r.width(), spot.top() - content_top), ov)
            painter.fillRect(QRect(r.left(), spot.top(), spot.left(), spot.height()), ov)
            painter.fillRect(QRect(spot.right(), spot.top(), r.right() - spot.right(), spot.height()), ov)
            painter.fillRect(QRect(r.left(), spot.bottom(), r.width(), r.bottom() - spot.bottom()), ov)
            painter.setPen(QPen(QColor("#1E293B"), 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(spot), 8, 8)
        else:
            painter.fillRect(QRect(r.left(), content_top, r.width(), r.height() - content_top), ov)

    def _go_prev(self):
        if self._step > 0:
            self._step -= 1
            self._update_step()

    def _go_next(self):
        if self._step < len(self._steps) - 1:
            self._step += 1
            self._update_step()

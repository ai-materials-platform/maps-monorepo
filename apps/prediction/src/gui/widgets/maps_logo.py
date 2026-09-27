from math import cos, radians, sin

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QLabel


def _paint_maps_logo(p: QPainter, S: int):
    """MAPS 로고 공통 페인팅 함수."""
    cx, cy = S / 2, S / 2
    sc = S / 44.0

    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    bg = QRadialGradient(cx - S * 0.1, cy - S * 0.1, S * 0.7)
    bg.setColorAt(0, QColor("#1E3A8A"))
    bg.setColorAt(1, QColor("#0F172A"))
    p.setBrush(bg)
    p.drawEllipse(QRectF(1, 1, S - 2, S - 2))

    p.setPen(QPen(QColor(59, 130, 246, 80), 1.2 * sc))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(2 * sc, 2 * sc, S - 4 * sc, S - 4 * sc))

    r_hex = 11 * sc
    hex_pts = [QPointF(cx + r_hex * cos(radians(i * 60 - 30)),
                       cy + r_hex * sin(radians(i * 60 - 30))) for i in range(6)]

    p.setPen(QPen(QColor(96, 165, 250, 160), 1.1 * sc))
    for i in range(6):
        p.drawLine(hex_pts[i], hex_pts[(i + 1) % 6])

    p.setPen(QPen(QColor(147, 197, 253, 120), 0.9 * sc))
    for pt in hex_pts:
        p.drawLine(QPointF(cx, cy), pt)

    face_pts = [QPointF((hex_pts[i].x() + hex_pts[(i+1) % 6].x()) / 2,
                        (hex_pts[i].y() + hex_pts[(i+1) % 6].y()) / 2) for i in range(6)]
    p.setPen(QPen(QColor(96, 165, 250, 100), 0.8 * sc))
    for pt in face_pts:
        p.drawLine(QPointF(cx, cy), pt)

    p.setPen(Qt.PenStyle.NoPen)
    for pt in hex_pts:
        glow = QRadialGradient(pt.x(), pt.y(), 4 * sc)
        glow.setColorAt(0, QColor(147, 197, 253, 200))
        glow.setColorAt(1, QColor(59, 130, 246, 0))
        p.setBrush(glow)
        p.drawEllipse(pt, 4 * sc, 4 * sc)
        p.setBrush(QColor(219, 234, 254))
        p.drawEllipse(pt, 2.2 * sc, 2.2 * sc)

    for pt in face_pts:
        p.setBrush(QColor(96, 165, 250, 180))
        p.drawEllipse(pt, 1.5 * sc, 1.5 * sc)

    center_glow = QRadialGradient(cx, cy, 6 * sc)
    center_glow.setColorAt(0, QColor(0, 210, 255, 220))
    center_glow.setColorAt(1, QColor(59, 130, 246, 0))
    p.setBrush(center_glow)
    p.drawEllipse(QPointF(cx, cy), 6 * sc, 6 * sc)
    p.setBrush(QColor(224, 242, 254))
    p.drawEllipse(QPointF(cx, cy), 3 * sc, 3 * sc)

    orbit_pen = QPen(QColor(59, 130, 246, 50), 0.8 * sc)
    orbit_pen.setStyle(Qt.PenStyle.DotLine)
    p.setPen(orbit_pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(cx, cy), 16 * sc, 16 * sc)


class MAPSLogoWidget(QLabel):
    """MAPS 앱 로고 — FCC 결정 격자 + 원자 궤도 표현."""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._sz = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    @staticmethod
    def as_icon(size: int = 64) -> QIcon:
        """창 아이콘으로 사용할 QIcon 반환."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        _paint_maps_logo(p, size)
        p.end()
        return QIcon(pixmap)

    def paintEvent(self, event):
        p = QPainter(self)
        _paint_maps_logo(p, self._sz)

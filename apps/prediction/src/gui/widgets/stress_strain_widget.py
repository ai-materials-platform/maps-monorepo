import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import (
    QColor, QBrush, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

SIMULATION_PHASE_COLORS = {
    "elastic": "#2563EB",
    "plastic": "#F59E0B",
    "necking": "#DC2626",
    "fracture": "#DC2626",
}


class StressStrainSimulationWidget(QWidget):
    state_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._colors = {
            "panel_bg": "#FFFFFF",
            "muted_bg": "#F8FAFC",
            "border": "#C9D2DC",
            "divider": "#CBD5E1",
            "text_primary": "#111827",
            "text_sec": "#334155",
            "text_label": "#64748B",
            "accent": "#1E293B",
        }
        self._dark_mode = False
        self._profile = None
        self._gauge_length_mm = 50.0
        self._width_mm = 2.0
        self._thickness_mm = 0.50
        self._drag_active = False
        self._hover_handle = False
        self._drag_origin_x = 0.0
        self._drag_origin_strain = 0.0
        self._drag_peak_strain = 0.0
        self._current_strain = 0.0
        self._peak_strain = 0.0
        self._residual_strain = 0.0
        self._release_target_strain = 0.0
        self._fractured = False
        self._fracture_lock_strain = None
        self._last_state_payload = None
        self._release_timer = QTimer(self)
        self._release_timer.setInterval(16)
        self._release_timer.timeout.connect(self._advance_release_animation)

    def has_profile(self):
        return self._profile is not None

    def set_theme(self, colors, dark_mode=False):
        self._colors = dict(self._colors, **colors)
        self._dark_mode = bool(dark_mode)
        self.update()

    def set_profile(self, strain_values, stress_values, meta):
        self._profile = {
            "strain": np.asarray(strain_values, dtype=float),
            "stress": np.asarray(stress_values, dtype=float),
            "meta": dict(meta),
        }
        self.reset_simulation(emit=False)
        self.update()
        self.emit_current_state()

    def clear_profile(self):
        self._profile = None
        self.reset_simulation(emit=False)
        self.update()
        self.emit_current_state()

    def set_assumptions(self, gauge_length_mm, width_mm, thickness_mm, preserve_state=False):
        self._gauge_length_mm = max(float(gauge_length_mm), 1.0)
        self._width_mm = max(float(width_mm), 0.05)
        self._thickness_mm = max(float(thickness_mm), 0.05)
        if not preserve_state:
            self.reset_simulation(emit=False)
        self.update()
        self.emit_current_state()

    def reset_simulation(self, emit=True):
        self._release_timer.stop()
        self._drag_active = False
        self._hover_handle = False
        self._drag_origin_x = 0.0
        self._drag_origin_strain = 0.0
        self._drag_peak_strain = 0.0
        self._current_strain = 0.0
        self._peak_strain = 0.0
        self._residual_strain = 0.0
        self._release_target_strain = 0.0
        self._fractured = False
        self._fracture_lock_strain = None
        self.unsetCursor()
        self.update()
        if emit:
            self.emit_current_state()

    def emit_current_state(self):
        payload = self._build_state_payload()
        self._last_state_payload = payload
        self.state_changed.emit(payload)

    def leaveEvent(self, event):
        if not self._drag_active:
            self._hover_handle = False
            self.unsetCursor()
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.has_profile()
            and not self._fractured
            and self._handle_rect().adjusted(-10.0, -12.0, 10.0, 12.0).contains(event.position())
        ):
            self._release_timer.stop()
            self._drag_active = True
            self._drag_origin_x = float(event.position().x())
            self._drag_origin_strain = self._current_strain
            self._drag_peak_strain = max(self._peak_strain, self._current_strain)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_active:
            if self._fractured and self._fracture_lock_strain is not None:
                self._current_strain = self._fracture_lock_strain
                self.update()
                self.emit_current_state()
                event.accept()
                return
            scene = self._scene_geometry()
            drag_fraction = (float(event.position().x()) - self._drag_origin_x) / max(scene["drag_span"], 1.0)
            candidate_strain = self._drag_origin_strain + drag_fraction * self._max_visual_strain()
            candidate_strain = float(np.clip(candidate_strain, 0.0, self._max_visual_strain()))
            self._drag_peak_strain = max(self._drag_peak_strain, candidate_strain)
            candidate_floor = self._residual_strain_for_peak(max(self._peak_strain, self._drag_peak_strain))
            candidate_strain = max(candidate_strain, candidate_floor)
            fracture_strain = self._fracture_strain()
            if candidate_strain >= fracture_strain:
                self._fractured = True
                self._peak_strain = max(self._peak_strain, fracture_strain)
                self._residual_strain = max(self._residual_strain, self._residual_strain_for_peak(fracture_strain))
                self._fracture_lock_strain = fracture_strain
                self._current_strain = fracture_strain
                self.update()
                self.emit_current_state()
                event.accept()
                return
            self._current_strain = candidate_strain
            self.update()
            self.emit_current_state()
            event.accept()
            return
        self._update_hover_state(event.position())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_active:
            self._drag_active = False
            self._update_hover_state(event.position())
            if self._fractured:
                self._release_target_strain = self._residual_strain
                self.emit_current_state()
                event.accept()
                return
            self._peak_strain = max(self._peak_strain, self._drag_peak_strain, self._current_strain)
            self._residual_strain = max(self._residual_strain, self._residual_strain_for_peak(self._peak_strain))
            mechanical = self._mechanical_state()
            self._release_target_strain = max(self._residual_strain, float(mechanical["released_strain"]))
            if abs(self._release_target_strain - self._current_strain) <= 1e-4:
                self._current_strain = self._release_target_strain
                self.update()
                self.emit_current_state()
            else:
                self._release_timer.start()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(self._colors["panel_bg"]))

        scene = self._scene_geometry()
        panel_rect = self.rect().adjusted(6, 6, -6, -6)
        painter.setPen(QPen(QColor(self._colors["border"]), 1.2))
        painter.setBrush(QColor(self._colors["muted_bg"]))
        painter.drawRoundedRect(panel_rect, 14.0, 14.0)

        self._draw_anchor(painter, scene)
        if self._fractured:
            self._draw_fractured_specimen(painter, scene)
        else:
            self._draw_intact_specimen(painter, scene, preview_only=not self.has_profile())
        self._draw_handle(painter, scene, enabled=self.has_profile())

        if not self.has_profile():
            painter.setPen(QColor(self._colors["text_sec"]))
            title_font = QFont()
            title_font.setPointSize(12)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.drawText(
                self.rect().adjusted(24, 24, -24, -80),
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter),
                "시뮬레이션 미리보기",
            )
            painter.setPen(QColor(self._colors["text_label"]))
            body_font = QFont()
            body_font.setPointSize(10)
            painter.setFont(body_font)
            painter.drawText(
                self.rect().adjusted(42, 52, -42, -80),
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter) | int(Qt.TextFlag.TextWordWrap),
                "먼저 물성 예측을 실행한 뒤, 오른쪽 주황색 핸들을 드래그해서 탄성 복원, 영구 변형, 파단 거동을 확인하세요.",
            )

    def _update_hover_state(self, position):
        hovering = bool(self._handle_rect().adjusted(-8.0, -10.0, 8.0, 10.0).contains(position))
        if hovering != self._hover_handle:
            self._hover_handle = hovering
            self.update()
        self.setCursor(Qt.CursorShape.OpenHandCursor if hovering else Qt.CursorShape.ArrowCursor)

    def _advance_release_animation(self):
        delta = self._release_target_strain - self._current_strain
        if abs(delta) <= 1e-4:
            self._current_strain = self._release_target_strain
            self._residual_strain = max(self._residual_strain, self._release_target_strain)
            self._release_timer.stop()
        else:
            self._current_strain += delta * 0.22
        self.update()
        self.emit_current_state()

    def _cross_section_area_mm2(self):
        return self._width_mm * self._thickness_mm

    def _fracture_strain(self):
        if not self.has_profile():
            return 0.12
        return max(float(self._profile["meta"].get("fracture_strain", 0.12)), 0.02)

    def _max_visual_strain(self):
        return max(self._fracture_strain() * 1.08, 0.03)

    def _dimension_ratios(self):
        return {
            "gauge": float(np.clip((self._gauge_length_mm - 10.0) / 140.0, 0.0, 1.0)),
            "width": float(np.clip((self._width_mm - 0.15) / 8.0, 0.0, 1.0)),
            "thickness": float(np.clip((self._thickness_mm - 0.05) / 2.0, 0.0, 1.0)),
            "area": float(np.clip((self._cross_section_area_mm2() - 0.1) / 8.0, 0.0, 1.0)),
        }

    def _scene_geometry(self):
        ratios = self._dimension_ratios()
        width = max(float(self.width()), 420.0)
        height = max(float(self.height()), 260.0)
        panel_margin = 20.0
        center_y = height * 0.55
        anchor_w = 32.0
        gauge_height = float(np.clip(16.0 + 16.0 * ratios["width"] + 18.0 * ratios["thickness"], 16.0, 60.0))
        grip_height = float(
            np.clip(gauge_height * (1.18 + 0.08 * ratios["area"]), gauge_height + 6.0, 84.0)
        )
        anchor_h = min(max(grip_height * 2.2, 108.0), height * 0.50)
        base_length = min(max(142.0 + 2.10 * self._gauge_length_mm, 142.0), width * 0.56)
        handle_w = float(np.clip(27.0 + 5.0 * ratios["width"], 27.0, 36.0))
        handle_h = float(np.clip(grip_height * 0.94, 42.0, 58.0))
        left_gap = 40.0
        connector_gap = 18.0
        anchor_left_offset = 34.0
        right_clearance = 28.0
        anchor_x = panel_margin + anchor_left_offset
        max_specimen_length = max(
            base_length,
            width
            - panel_margin
            - right_clearance
            - (anchor_x + anchor_w + left_gap + connector_gap + handle_w),
        )
        geometry_strain = (
            self._fracture_lock_strain
            if self._fractured and self._fracture_lock_strain is not None
            else self._current_strain
        )
        strain_ratio = min(geometry_strain / max(self._max_visual_strain(), 1e-6), 1.08)
        drag_span = max(max_specimen_length - base_length, 72.0)
        specimen_length = min(base_length + drag_span * strain_ratio, max_specimen_length)
        specimen_x = anchor_x + anchor_w + left_gap
        handle_left = specimen_x + specimen_length + connector_gap
        live_gauge_height = gauge_height
        if self.has_profile() and not self._fractured:
            uts_strain = float(self._profile["meta"].get("uts_strain", self._fracture_strain() * 0.7))
            if geometry_strain >= uts_strain:
                neck_ratio = (geometry_strain - uts_strain) / max(self._fracture_strain() - uts_strain, 1e-6)
                neck_ratio = float(np.clip(neck_ratio, 0.0, 1.0))
                live_gauge_height = max(gauge_height * (0.94 - 0.34 * neck_ratio), 14.0)
        if self._fractured:
            live_gauge_height = max(gauge_height * 0.56, 14.0)
        return {
            "width": width,
            "height": height,
            "center_y": center_y,
            "anchor_x": anchor_x,
            "anchor_w": anchor_w,
            "anchor_h": anchor_h,
            "specimen_x": specimen_x,
            "base_length": base_length,
            "specimen_length": max(specimen_length, 72.0),
            "drag_span": drag_span,
            "gauge_height": gauge_height,
            "live_gauge_height": live_gauge_height,
            "grip_height": grip_height,
            "handle_rect": (
                handle_left,
                center_y - handle_h / 2.0,
                handle_w,
                handle_h,
            ),
        }

    def _handle_rect(self):
        x, y, w, h = self._scene_geometry()["handle_rect"]
        return self._qrectf(x, y, w, h)

    def _reference_line_pen(self):
        pen = QPen(QColor(self._colors["divider"]), 1.3, Qt.PenStyle.DashLine)
        pen.setDashPattern([5.0, 4.0])
        return pen

    def _draw_reference_line(self, painter, scene):
        pen = self._reference_line_pen()
        painter.setPen(pen)
        y = scene["center_y"] + max(scene["grip_height"] * 1.05, 48.0)
        painter.drawLine(
            int(scene["anchor_x"] + scene["anchor_w"] + 12.0),
            int(y),
            int(scene["width"] - 32.0),
            int(y),
        )

    def _draw_anchor(self, painter, scene):
        anchor_rect = self._qrectf(
            scene["anchor_x"],
            scene["center_y"] - scene["anchor_h"] / 2.0,
            scene["anchor_w"],
            scene["anchor_h"],
        )
        fill = QColor("#0F172A" if not self._dark_mode else "#E2E8F0")
        line = QColor("#111827" if not self._dark_mode else "#F8FAFC")
        painter.setPen(QPen(line, 2.0))
        painter.setBrush(QColor(self._colors["panel_bg"]))
        painter.drawRoundedRect(anchor_rect, 4.0, 4.0)
        painter.save()
        painter.setClipRect(anchor_rect)
        stripe_pen = QPen(fill, 2.0)
        painter.setPen(stripe_pen)
        start_x = anchor_rect.left() - 28.0
        end_x = anchor_rect.right() + 28.0
        y = anchor_rect.top() - 6.0
        while y <= anchor_rect.bottom() + 24.0:
            painter.drawLine(int(start_x), int(y), int(end_x), int(y + 34.0))
            y += 14.0
        painter.restore()
        painter.setBrush(QColor(fill.red(), fill.green(), fill.blue(), 60))
        painter.setPen(QPen(QColor(line.red(), line.green(), line.blue(), 90), 1.2))
        for offset in [-scene["anchor_h"] * 0.22, scene["anchor_h"] * 0.22]:
            painter.drawEllipse(
                self._qrectf(
                    scene["anchor_x"] + 8.0,
                    scene["center_y"] + offset - 5.0,
                    14.0,
                    14.0,
                )
            )
        painter.setPen(QPen(line, 2.2))
        painter.drawLine(
            int(anchor_rect.right()),
            int(scene["center_y"]),
            int(scene["specimen_x"] - 8.0),
            int(scene["center_y"]),
        )
        label_font = QFont()
        label_font.setPointSize(9)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QColor(self._colors["text_sec"]))
        painter.drawText(
            self._qrectf(scene["anchor_x"] - 24.0, anchor_rect.top() - 28.0, 96.0, 18.0),
            int(Qt.AlignmentFlag.AlignCenter),
            "왼쪽 고정단",
        )

    def _draw_dimension_guides(self, painter, scene):
        current_length = scene["specimen_length"]
        gauge_height = scene["live_gauge_height"] if self.has_profile() else scene["gauge_height"]
        gauge_left = scene["specimen_x"] + current_length * 0.29
        gauge_right = scene["specimen_x"] + current_length * 0.69
        gauge_center_x = (gauge_left + gauge_right) / 2.0
        gauge_top = scene["center_y"] - gauge_height / 2.0
        gauge_bottom = scene["center_y"] + gauge_height / 2.0
        handle_rect = self._handle_rect()
        state = self._mechanical_state()

        top_rect = self._qrectf(gauge_center_x - 88.0, gauge_top - 54.0, 176.0, 28.0)
        self._draw_callout(
            painter,
            top_rect,
            (gauge_center_x, gauge_top),
            f"가운데 표점부 {self._gauge_length_mm:.1f} mm",
        )

        bottom_rect = self._qrectf(gauge_center_x - 150.0, gauge_bottom + 16.0, 300.0, 32.0)
        self._draw_callout(
            painter,
            bottom_rect,
            (gauge_center_x, gauge_bottom),
            (
                f"폭 {self._width_mm:.2f} mm  |  "
                f"두께 {self._thickness_mm:.2f} mm  |  "
                f"단면적 {self._cross_section_area_mm2():.2f} mm²"
            ),
        )

        handle_rect_box = self._qrectf(handle_rect.left() - 34.0, handle_rect.top() - 48.0, 96.0, 30.0)
        self._draw_callout(
            painter,
            handle_rect_box,
            (handle_rect.center().x(), handle_rect.top()),
            "주황색 핸들",
        )

        if state["phase"] == "necking":
            focus_x = scene["specimen_x"] + current_length * 0.62
            focus_rect = self._qrectf(focus_x - 76.0, gauge_top - 92.0, 152.0, 34.0)
            self._draw_callout(
                painter,
                focus_rect,
                (focus_x, scene["center_y"]),
                "이 구간이 가장 먼저 가늘어집니다",
            )
        elif state["phase"] == "fracture":
            focus_x = scene["specimen_x"] + current_length * 0.58
            focus_rect = self._qrectf(focus_x - 72.0, gauge_top - 92.0, 144.0, 34.0)
            self._draw_callout(
                painter,
                focus_rect,
                (focus_x, scene["center_y"]),
                "이 부근에서 파단이 발생합니다",
            )

    def _draw_callout(self, painter, rect, anchor_point, text):
        fill = QColor("#FFFFFF" if not self._dark_mode else "#1E293B")
        fill.setAlpha(228 if not self._dark_mode else 214)
        border = QColor(self._colors["border"])
        text_color = QColor(self._colors["text_sec"])
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 11.0, 11.0)

        ax, ay = anchor_point
        attach_x = min(max(ax, rect.left() + 12.0), rect.right() - 12.0)
        if ay < rect.top():
            attach_y = rect.top()
        elif ay > rect.bottom():
            attach_y = rect.bottom()
        elif ax < rect.left():
            attach_x = rect.left()
            attach_y = min(max(ay, rect.top() + 8.0), rect.bottom() - 8.0)
        else:
            attach_x = rect.right()
            attach_y = min(max(ay, rect.top() + 8.0), rect.bottom() - 8.0)

        painter.setPen(QPen(border, 1.0))
        painter.drawLine(int(ax), int(ay), int(attach_x), int(attach_y))
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(
            rect.adjusted(10.0, 0.0, -10.0, 0.0),
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            text,
        )

    def _paint_specimen_path(self, painter, path, start_color, end_color):
        bounds = path.boundingRect()
        shadow = path.translated(0.0, 4.0)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(QColor(15, 23, 42, 24 if not self._dark_mode else 42))
        painter.drawPath(shadow)

        gradient = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.bottom())
        gradient.setColorAt(0.0, QColor(start_color).darker(106 if not self._dark_mode else 128))
        gradient.setColorAt(0.16, QColor(start_color))
        gradient.setColorAt(0.48, QColor(255, 255, 255, 128 if not self._dark_mode else 54))
        gradient.setColorAt(0.80, QColor(end_color))
        gradient.setColorAt(1.0, QColor(end_color).darker(114 if not self._dark_mode else 132))
        outline = QColor("#0F172A" if not self._dark_mode else "#F8FAFC")
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(outline, 2.1))
        painter.drawPath(path)

        painter.save()
        painter.setClipPath(path)
        sheen = QLinearGradient(bounds.left(), bounds.center().y(), bounds.right(), bounds.center().y())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.18, QColor(255, 255, 255, 26 if not self._dark_mode else 10))
        sheen.setColorAt(0.50, QColor(255, 255, 255, 76 if not self._dark_mode else 22))
        sheen.setColorAt(0.82, QColor(255, 255, 255, 18 if not self._dark_mode else 8))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(bounds, QBrush(sheen))

        painter.setPen(QPen(QColor(255, 255, 255, 118 if not self._dark_mode else 54), 1.1))
        painter.drawLine(
            int(bounds.left() + 12.0),
            int(bounds.top() + 6.0),
            int(bounds.right() - 14.0),
            int(bounds.top() + 9.0),
        )
        painter.setPen(QPen(QColor(148, 163, 184, 92 if not self._dark_mode else 116), 1.0))
        for ratio in [0.26, 0.40, 0.55, 0.70]:
            y = bounds.top() + bounds.height() * ratio
            painter.drawLine(
                int(bounds.left() + 14.0),
                int(y),
                int(bounds.right() - 16.0),
                int(y),
            )
        painter.setPen(QPen(QColor(71, 85, 105, 55 if not self._dark_mode else 85), 1.0))
        painter.drawLine(
            int(bounds.left() + 16.0),
            int(bounds.bottom() - 7.0),
            int(bounds.right() - 18.0),
            int(bounds.bottom() - 10.0),
        )
        painter.restore()

    def _draw_connector(self, painter, start_x, center_y):
        handle_rect = self._handle_rect()
        cable = QPainterPath()
        cable.moveTo(start_x, center_y)
        cable.cubicTo(
            start_x + 12.0,
            center_y + 6.0,
            handle_rect.left() - 12.0,
            center_y + 6.0,
            handle_rect.left(),
            center_y,
        )
        painter.setPen(QPen(QColor("#1F2937" if not self._dark_mode else "#E5E7EB"), 2.0))
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawPath(cable)

    def _draw_intact_specimen(self, painter, scene, preview_only=False):
        current_length = scene["specimen_length"]
        grip_height = scene["grip_height"]
        gauge_height = scene["gauge_height"] * 0.92 if preview_only else scene["live_gauge_height"]
        path = self._create_specimen_path(
            scene["specimen_x"],
            scene["center_y"],
            current_length,
            grip_height,
            gauge_height,
        )
        if preview_only:
            start_color = QColor("#E5E7EB" if not self._dark_mode else "#64748B")
            end_color = QColor("#CBD5E1" if not self._dark_mode else "#475569")
        else:
            start_color = QColor("#F8FAFC" if not self._dark_mode else "#CBD5E1")
            end_color = QColor("#D3DAE4" if not self._dark_mode else "#64748B")
        self._paint_specimen_path(painter, path, start_color, end_color)
        self._draw_connector(painter, scene["specimen_x"] + current_length, scene["center_y"])
        self._draw_dimension_guides(painter, scene)

    def _draw_fractured_specimen(self, painter, scene):
        handle_rect = self._handle_rect()
        current_length = scene["specimen_length"]
        gap = min(max(current_length * 0.08, 22.0), 34.0)
        right_piece_len = max(scene["base_length"] * 0.18, 42.0)
        right_piece_x = handle_rect.left() - right_piece_len - 18.0
        left_piece_len = max(right_piece_x - scene["specimen_x"] - gap, scene["base_length"] * 0.54)
        gauge_height = max(scene["live_gauge_height"], 14.0)
        left_edge_points = self._fracture_edge_points(
            scene["specimen_x"] + left_piece_len,
            scene["center_y"],
            max(gauge_height * 1.02, 14.0),
            reverse=False,
        )
        right_edge_points = self._fracture_edge_points(
            right_piece_x,
            scene["center_y"],
            max(gauge_height * 0.90, 12.0),
            reverse=True,
        )

        left_path = self._create_fractured_piece_path(
            scene["specimen_x"],
            scene["center_y"],
            left_piece_len,
            scene["grip_height"],
            gauge_height,
            broken_side="right",
            edge_points=left_edge_points,
        )
        right_path = self._create_fractured_piece_path(
            right_piece_x,
            scene["center_y"],
            right_piece_len,
            max(scene["grip_height"] * 0.92, gauge_height * 1.12),
            max(gauge_height * 0.78, 12.0),
            broken_side="left",
            edge_points=right_edge_points,
        )
        self._paint_specimen_path(
            painter,
            left_path,
            QColor("#E5E7EB" if not self._dark_mode else "#94A3B8"),
            QColor("#CDD6E1" if not self._dark_mode else "#64748B"),
        )
        self._paint_specimen_path(
            painter,
            right_path,
            QColor("#F1F5F9" if not self._dark_mode else "#CBD5E1"),
            QColor("#D3DAE4" if not self._dark_mode else "#64748B"),
        )
        self._draw_broken_edge(painter, left_edge_points)
        self._draw_broken_edge(painter, right_edge_points)
        self._draw_connector(painter, right_piece_x + right_piece_len, scene["center_y"])
        self._draw_dimension_guides(painter, scene)

    def _fracture_edge_points(self, x_pos, center_y, height, reverse=False):
        y_top = center_y - height / 2.0
        amplitude = min(8.5, max(height * 0.14, 3.5))
        offsets = np.array([0.0, 0.28, -0.16, 0.42, -0.30, 0.24, -0.10, 0.0]) * amplitude
        if reverse:
            offsets *= -1.0
        y_ratios = np.array([0.0, 0.12, 0.27, 0.44, 0.61, 0.78, 0.91, 1.0])
        return [(x_pos + float(dx), y_top + float(height * ratio)) for dx, ratio in zip(offsets, y_ratios)]

    def _append_smooth_points(self, path, points):
        if len(points) < 2:
            return
        for idx in range(1, len(points)):
            prev_x, prev_y = points[idx - 1]
            cur_x, cur_y = points[idx]
            mid_x = (prev_x + cur_x) / 2.0
            mid_y = (prev_y + cur_y) / 2.0
            path.quadTo(prev_x, prev_y, mid_x, mid_y)
        path.lineTo(points[-1][0], points[-1][1])

    def _create_fractured_piece_path(self, x_pos, center_y, length, grip_height, gauge_height, broken_side, edge_points):
        length = max(length, 40.0)
        grip_top = center_y - grip_height / 2.0
        gauge_top = center_y - gauge_height / 2.0
        grip_bottom = center_y + grip_height / 2.0
        gauge_bottom = center_y + gauge_height / 2.0
        radius = min(7.0, grip_height / 4.0)
        shoulder_pull = max((grip_height - gauge_height) * 0.32, 2.0)

        if broken_side == "right":
            left_grip_len = length * 0.22
            transition_len = min(max(length * 0.10, 16.0), 30.0)
            x0 = x_pos
            x1 = x0 + left_grip_len
            x2 = min(x1 + transition_len, x0 + length - 12.0)
            path = QPainterPath()
            path.moveTo(x0 + radius, grip_top)
            path.lineTo(x1, grip_top)
            path.quadTo(x1 + transition_len * 0.42, grip_top + shoulder_pull, x2, gauge_top)
            path.lineTo(edge_points[0][0], edge_points[0][1])
            self._append_smooth_points(path, edge_points)
            path.lineTo(x2, gauge_bottom)
            path.quadTo(x1 + transition_len * 0.42, grip_bottom - shoulder_pull, x1, grip_bottom)
            path.lineTo(x0 + radius, grip_bottom)
            path.quadTo(x0, grip_bottom, x0, grip_bottom - radius)
            path.lineTo(x0, grip_top + radius)
            path.quadTo(x0, grip_top, x0 + radius, grip_top)
            path.closeSubpath()
            return path

        right_grip_len = min(max(length * 0.26, 14.0), length * 0.46)
        transition_len = min(max(length * 0.12, 12.0), 22.0)
        x0 = x_pos
        x4 = x0 + length
        x3 = x4 - right_grip_len
        x2 = max(x3 - transition_len, x0 + 14.0)
        path = QPainterPath()
        path.moveTo(edge_points[0][0], edge_points[0][1])
        path.lineTo(x2, gauge_top)
        path.quadTo(x3 - transition_len * 0.42, grip_top + shoulder_pull, x3, grip_top)
        path.lineTo(x4 - radius, grip_top)
        path.quadTo(x4, grip_top, x4, grip_top + radius)
        path.lineTo(x4, grip_bottom - radius)
        path.quadTo(x4, grip_bottom, x4 - radius, grip_bottom)
        path.lineTo(x3, grip_bottom)
        path.quadTo(x3 - transition_len * 0.42, grip_bottom - shoulder_pull, x2, gauge_bottom)
        path.lineTo(edge_points[-1][0], edge_points[-1][1])
        self._append_smooth_points(path, list(reversed(edge_points)))
        path.closeSubpath()
        return path

    def _draw_broken_edge(self, painter, points):
        crack = QPainterPath()
        crack.moveTo(points[0][0], points[0][1])
        self._append_smooth_points(crack, points)
        pen = QPen(QColor("#7F1D1D" if not self._dark_mode else "#FCA5A5"), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawPath(crack)

    def _draw_handle(self, painter, scene, enabled=True):
        handle_rect = self._handle_rect()
        fill = QColor("#FB923C" if enabled else "#CBD5E1")
        if self._drag_active:
            fill = QColor("#F97316")
        elif self._hover_handle:
            fill = QColor("#FDBA74" if enabled else "#CBD5E1")
        border = QColor("#EA580C" if enabled else self._colors["border"])
        painter.setPen(QPen(border, 2.1))
        painter.setBrush(fill)
        painter.drawRoundedRect(handle_rect, 6.0, 6.0)
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1.1))
        for offset in [-6.0, 0.0, 6.0]:
            painter.drawLine(
                int(handle_rect.left() + 6.0),
                int(handle_rect.center().y() + offset),
                int(handle_rect.right() - 6.0),
                int(handle_rect.center().y() + offset),
            )

    def _create_specimen_path(self, x_pos, center_y, length, grip_height, gauge_height):
        length = max(length, 82.0)
        left_grip_len = length * 0.17
        right_grip_len = length * 0.15
        transition_len = min(max(length * 0.09, 16.0), 34.0)
        x0 = x_pos
        x1 = x0 + left_grip_len
        x2 = x1 + transition_len
        x5 = x_pos + length
        x4 = x5 - right_grip_len
        x3 = max(x4 - transition_len, x2 + 26.0)
        grip_top = center_y - grip_height / 2.0
        gauge_top = center_y - gauge_height / 2.0
        grip_bottom = center_y + grip_height / 2.0
        gauge_bottom = center_y + gauge_height / 2.0
        radius = min(7.0, grip_height / 4.0)
        shoulder_pull = max((grip_height - gauge_height) * 0.32, 2.0)

        path = QPainterPath()
        path.moveTo(x0 + radius, grip_top)
        path.lineTo(x1, grip_top)
        path.quadTo(x1 + transition_len * 0.42, grip_top + shoulder_pull, x2, gauge_top)
        path.lineTo(x3, gauge_top)
        path.quadTo(x4 - transition_len * 0.42, grip_top + shoulder_pull, x4, grip_top)
        path.lineTo(x5 - radius, grip_top)
        path.quadTo(x5, grip_top, x5, grip_top + radius)
        path.lineTo(x5, grip_bottom - radius)
        path.quadTo(x5, grip_bottom, x5 - radius, grip_bottom)
        path.lineTo(x4, grip_bottom)
        path.quadTo(x4 - transition_len * 0.42, grip_bottom - shoulder_pull, x3, gauge_bottom)
        path.lineTo(x2, gauge_bottom)
        path.quadTo(x1 + transition_len * 0.42, grip_bottom - shoulder_pull, x1, grip_bottom)
        path.lineTo(x0 + radius, grip_bottom)
        path.quadTo(x0, grip_bottom, x0, grip_bottom - radius)
        path.lineTo(x0, grip_top + radius)
        path.quadTo(x0, grip_top, x0 + radius, grip_top)
        path.closeSubpath()
        return path

    def _stress_for_strain(self, strain):
        if not self.has_profile() or strain <= 0.0:
            return 0.0
        fracture_strain = self._fracture_strain()
        if self._fractured or strain >= fracture_strain:
            return 0.0
        return self._profile_stress_at(strain)

    def _profile_stress_at(self, strain):
        if not self.has_profile() or strain <= 0.0:
            return 0.0
        return float(
            np.interp(
                strain,
                self._profile["strain"],
                self._profile["stress"],
                left=0.0,
                right=float(self._profile["stress"][-1]),
            )
        )

    def _residual_strain_for_peak(self, peak_strain):
        if not self.has_profile() or peak_strain <= 0.0:
            return 0.0
        meta = self._profile["meta"]
        yield_strain = float(meta.get("yield_strain", 0.002))
        fracture_strain = self._fracture_strain()
        if peak_strain < yield_strain:
            return 0.0
        if peak_strain >= fracture_strain:
            return max(fracture_strain * 0.78, yield_strain * 1.2)

        uts_strain = float(meta.get("uts_strain", max(yield_strain + 0.01, fracture_strain * 0.7)))
        elastic_modulus = max(float(meta.get("elastic_modulus_gpa", 190.0)) * 1000.0, 1.0)
        envelope_stress_mpa = self._profile_stress_at(peak_strain)
        residual_strain = max(peak_strain - (envelope_stress_mpa / elastic_modulus), 0.0)
        if peak_strain >= uts_strain:
            necking_progress = float(
                np.clip(
                    (peak_strain - uts_strain) / max(fracture_strain - uts_strain, 1e-6),
                    0.0,
                    1.0,
                )
            )
            retained_necking_strain = min(
                peak_strain,
                uts_strain + (peak_strain - uts_strain) * (0.62 + 0.20 * necking_progress),
            )
            residual_strain = max(residual_strain, retained_necking_strain)
        return min(residual_strain, peak_strain)

    def _active_peak_strain(self):
        peak_strain = self._peak_strain
        if self._drag_active:
            peak_strain = max(peak_strain, self._drag_peak_strain, self._current_strain)
        if self._fractured and self._fracture_lock_strain is not None:
            peak_strain = max(peak_strain, self._fracture_lock_strain)
        return peak_strain

    def _mechanical_state(self):
        area_mm2 = self._cross_section_area_mm2()
        extension_mm = self._current_strain * self._gauge_length_mm
        if not self.has_profile():
            return {
                "phase": "placeholder",
                "title": "시뮬레이션 준비",
                "subtitle": "예측을 실행한 뒤 주황색 핸들을 드래그해 보세요.",
                "accent_color": self._colors["text_sec"],
                "stress_mpa": 0.0,
                "force_n": 0.0,
                "strain": 0.0,
                "extension_mm": 0.0,
                "permanent_extension_mm": 0.0,
                "released_strain": 0.0,
                "area_mm2": area_mm2,
                "is_releasing": False,
                "is_unloaded": False,
                "reference_force_n": 0.0,
                "reference_stress_mpa": 0.0,
            }
        meta = self._profile["meta"]
        yield_strain = float(meta.get("yield_strain", 0.002))
        uts_strain = float(meta.get("uts_strain", max(yield_strain + 0.01, self._fracture_strain() * 0.7)))
        fracture_strain = self._fracture_strain()
        elastic_modulus = max(float(meta.get("elastic_modulus_gpa", 190.0)) * 1000.0, 1.0)
        active_peak_strain = self._active_peak_strain()
        residual_floor_strain = max(self._residual_strain, self._residual_strain_for_peak(active_peak_strain))

        if self._fractured or self._current_strain >= fracture_strain:
            residual_strain = max(residual_floor_strain, self._residual_strain_for_peak(fracture_strain))
            fracture_probe = min(
                max(fracture_strain - 1e-4, fracture_strain * 0.995),
                float(self._profile["strain"][-1]),
            )
            fracture_stress_mpa = self._profile_stress_at(fracture_probe)
            return {
                "phase": "fracture",
                "title": "파단",
                "subtitle": "하중을 더 지탱하지 못하고 시편이 끊어졌습니다.",
                "accent_color": SIMULATION_PHASE_COLORS["fracture"],
                "stress_mpa": 0.0,
                "force_n": 0.0,
                "strain": max(self._current_strain, fracture_strain),
                "extension_mm": extension_mm,
                "permanent_extension_mm": residual_strain * self._gauge_length_mm,
                "released_strain": residual_strain,
                "area_mm2": area_mm2,
                "is_releasing": False,
                "is_unloaded": True,
                "reference_force_n": fracture_stress_mpa * area_mm2,
                "reference_stress_mpa": fracture_stress_mpa,
            }

        envelope_stress_mpa = self._stress_for_strain(self._current_strain)
        reloading_stress_mpa = elastic_modulus * max(self._current_strain - residual_floor_strain, 0.0)
        loaded_stress_mpa = min(envelope_stress_mpa, reloading_stress_mpa)
        elastic_recovery_strain = min(loaded_stress_mpa / elastic_modulus, self._current_strain)
        target_residual_strain = max(residual_floor_strain, self._current_strain - elastic_recovery_strain)
        residual_strain = self._release_target_strain if (not self._drag_active and self._release_target_strain > 0.0) else target_residual_strain
        loaded_force_n = loaded_stress_mpa * area_mm2
        is_releasing = (
            not self._drag_active
            and self._current_strain > self._release_target_strain + 2e-4
            and self._release_target_strain >= 0.0
        )
        is_unloaded = (
            not self._drag_active
            and self._release_target_strain > 0.0
            and abs(self._current_strain - self._release_target_strain) <= 2e-4
        )
        stress_mpa = 0.0 if (is_releasing or is_unloaded) else loaded_stress_mpa
        force_n = 0.0 if (is_releasing or is_unloaded) else loaded_force_n

        if self._current_strain <= 1e-6 and not self._drag_active:
            phase = "ready"
            title = "준비"
            subtitle = "오른쪽 주황색 핸들을 드래그해 하중을 걸어보세요."
            accent_color = self._colors["text_sec"]
        elif self._current_strain < yield_strain:
            phase = "elastic"
            title = "탄성 영역"
            subtitle = "손을 놓으면 원래 길이로 거의 복원됩니다."
            accent_color = SIMULATION_PHASE_COLORS["elastic"]
        elif self._current_strain < uts_strain:
            phase = "plastic"
            title = "소성 변형"
            subtitle = "일부만 복원되고 영구 변형이 남기 시작합니다."
            accent_color = SIMULATION_PHASE_COLORS["plastic"]
        else:
            phase = "necking"
            title = "국부 수축"
            subtitle = "국부 단면 축소가 커져 파단에 가까운 상태입니다."
            accent_color = SIMULATION_PHASE_COLORS["necking"]

        if is_releasing:
            title = "복원 중"
            subtitle = "외력을 놓아 탄성분이 다시 줄어드는 중입니다."
        elif is_unloaded:
            title = "영구 변형"
            subtitle = "외력은 0 N까지 줄었지만 늘어난 길이는 일부 남아 있습니다."

        return {
            "phase": phase,
            "title": title,
            "subtitle": subtitle,
            "accent_color": accent_color,
            "stress_mpa": stress_mpa,
            "force_n": force_n,
            "strain": self._current_strain,
            "extension_mm": extension_mm,
            "permanent_extension_mm": residual_strain * self._gauge_length_mm,
            "released_strain": residual_strain,
            "area_mm2": area_mm2,
            "is_releasing": is_releasing,
            "is_unloaded": is_unloaded,
            "reference_force_n": loaded_force_n,
            "reference_stress_mpa": loaded_stress_mpa,
        }

    def _build_state_payload(self):
        state = self._mechanical_state()
        assumption = (
            f"가정 시편: 표점거리 {self._gauge_length_mm:.1f} mm | "
            f"폭 {self._width_mm:.2f} mm | 두께 {self._thickness_mm:.2f} mm | "
            f"단면적 {state['area_mm2']:.2f} mm²"
        )
        if state["phase"] == "placeholder":
            detail = (
                "왼쪽 고정단은 그대로 유지되고, 가운데 표점부가 늘어나며, 오른쪽 주황색 핸들이 당기는 위치입니다.\n"
                "예측을 실행한 뒤 핸들을 드래그하면 응력, 하중, 복원 여부를 실시간으로 확인할 수 있습니다."
            )
        elif state["phase"] == "fracture":
            detail = (
                f"파단 직전 외력 {self._format_force(state['reference_force_n'])} | "
                f"파단 직전 응력 {state['reference_stress_mpa']:.1f} MPa | "
                f"파단 시점 변형률 {self._fracture_strain() * 100.0:.2f}%\n"
                f"가운데 표점부 중에서도 가장 가늘어진 구간에서 자연스럽게 벌어지며 끊어진 상태입니다. 잔류 연신은 약 {state['permanent_extension_mm']:.2f} mm 입니다."
            )
        elif state.get("is_releasing"):
            detail = (
                "현재 외력 0.0 N (0 gf) | 마우스를 놓아 탄성 복원이 진행 중입니다.\n"
                f"왼쪽 고정단은 그대로이고, 가운데 표점부가 다시 줄어들고 있습니다. 최종적으로 남는 잔류 연신은 약 {state['permanent_extension_mm']:.2f} mm 입니다."
            )
        elif state.get("is_unloaded"):
            detail = (
                "현재 외력 0.0 N (0 gf) | 손을 놓아 탄성분은 되돌아간 상태입니다.\n"
                f"왼쪽 고정단은 그대로이고, 가운데 표점부가 일부 줄어들었지만 완전히 돌아오지는 않아 잔류 연신 {state['permanent_extension_mm']:.2f} mm 가 남아 있습니다."
            )
        else:
            detail = (
                f"현재 외력 {self._format_force(state['force_n'])} | "
                f"응력 {state['stress_mpa']:.1f} MPa | "
                f"변형률 {state['strain'] * 100.0:.2f}% | "
                f"연신 {state['extension_mm']:.2f} mm"
            )
            if state["phase"] == "elastic":
                detail += (
                    "\n가운데 표점부 전체가 비교적 고르게 늘어나며, 손을 놓으면 이 중앙부가 다시 줄어들어 원래 길이에 가깝게 복원됩니다."
                )
            elif state["phase"] == "plastic":
                detail += (
                    "\n가운데 표점부에서 먼저 영구 변형이 쌓이기 시작한 단계입니다. 손을 놓으면 힘은 줄어들지만 중앙부 길이는 일부 남습니다."
                )
            elif state["phase"] == "necking":
                detail += (
                    "\n가운데 표점부, 특히 가늘어진 집중 구간이 더 빨리 줄어들고 있어 이 부근이 파단 후보 위치입니다."
                )
        return {
            "phase": state["phase"],
            "headline": f"{state['title']} | {state['subtitle']}",
            "detail": detail,
            "assumption": (
                assumption
                + " | 하중은 지금 마우스로 당기고 있는 외력입니다. 손을 놓아 잔류 상태가 되면 외력은 0 N으로 내려가고, 남는 값은 잔류 변형입니다."
            ),
            "accent_color": state["accent_color"],
            "current_strain": self._current_strain,
            "current_stress_mpa": state.get("stress_mpa", 0.0),
        }

    @staticmethod
    def _format_force(force_n):
        if force_n <= 0.0:
            return "0.0 N (0 gf)"
        kgf = force_n / 9.80665
        if kgf >= 1.0:
            mass_text = f"{kgf:.2f} kgf"
        else:
            mass_text = f"{kgf * 1000.0:.0f} gf"
        return f"{force_n:.1f} N ({mass_text})"

    @staticmethod
    def _qrectf(x_pos, y_pos, width, height):
        return QRectF(float(x_pos), float(y_pos), float(width), float(height))

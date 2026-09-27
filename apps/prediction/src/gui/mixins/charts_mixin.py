import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.gui.constants import CURVE_SEGMENT_STYLES
from src.gui.widgets import StressStrainSimulationWidget, StrainExploreDialog


class ChartsMixin:
    def _create_curve_legend_card(self):
        card = QFrame()
        card.setMinimumWidth(180)
        card.setMaximumWidth(260)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        for segment_name in ["elastic", "hardening", "necking"]:
            text_label = QLabel(CURVE_SEGMENT_STYLES[segment_name]["legend_html"])
            text_label.setTextFormat(Qt.TextFormat.RichText)
            text_label.setWordWrap(True)
            layout.addWidget(text_label)
            self._curve_legend_label_widgets.append(text_label)

        self._curve_legend_cards.append(card)
        return card

    def _create_curve_info_panel(self, text_attr_name, legend_attr_name):
        panel = QFrame()
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(12, 16, 12, 12)
        panel_layout.setSpacing(12)

        text_label = QLabel("")
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        panel_layout.addWidget(text_label, 1)

        setattr(self, text_attr_name, text_label)
        setattr(self, legend_attr_name, None)
        self._curve_info_panels.append(panel)
        return panel

    def _create_simulation_tab(self, prefix):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        status_label = QLabel("")
        status_label.setWordWrap(True)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_label = QLabel("")
        detail_label.setWordWrap(True)
        detail_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        assumption_label = QLabel("")
        assumption_label.setWordWrap(True)
        assumption_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        info_layout.addWidget(status_label)
        info_layout.addWidget(detail_label)
        info_layout.addWidget(assumption_label)

        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setFrameShape(QFrame.Shape.NoFrame)
        info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        info_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        info_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        info_scroll.setMinimumHeight(100)
        info_scroll.setMaximumHeight(200)
        info_scroll.setWidget(info_panel)

        control_card = QFrame()
        control_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        control_layout = QGridLayout(control_card)
        control_layout.setContentsMargins(14, 10, 14, 10)
        control_layout.setHorizontalSpacing(12)
        control_layout.setVerticalSpacing(6)
        control_layout.setRowMinimumHeight(0, 18)
        control_layout.setRowMinimumHeight(1, 36)

        gauge_spin = QDoubleSpinBox()
        gauge_spin.setRange(5.0, 200.0)
        gauge_spin.setDecimals(1)
        gauge_spin.setSingleStep(5.0)
        gauge_spin.setValue(50.0)
        gauge_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        gauge_spin.setKeyboardTracking(False)
        gauge_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gauge_spin.setMinimumSize(96, 36)

        width_spin = QDoubleSpinBox()
        width_spin.setRange(0.1, 50.0)
        width_spin.setDecimals(2)
        width_spin.setSingleStep(0.25)
        width_spin.setValue(2.0)
        width_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        width_spin.setKeyboardTracking(False)
        width_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        width_spin.setMinimumSize(96, 36)

        thickness_spin = QDoubleSpinBox()
        thickness_spin.setRange(0.05, 20.0)
        thickness_spin.setDecimals(2)
        thickness_spin.setSingleStep(0.05)
        thickness_spin.setValue(0.50)
        thickness_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        thickness_spin.setKeyboardTracking(False)
        thickness_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thickness_spin.setMinimumSize(96, 36)

        area_value_label = QLabel("")
        area_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        area_value_label.setMinimumSize(96, 36)
        area_value_label.setProperty("simulation_role", "value")

        for col, (caption, widget) in enumerate(
            [
                ("표점거리 (mm)", gauge_spin),
                ("폭 (mm)", width_spin),
                ("두께 (mm)", thickness_spin),
                ("단면적 (mm²)", area_value_label),
            ]
        ):
            caption_label = QLabel(caption)
            caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption_label.setProperty("simulation_role", "caption")
            caption_label.setMinimumHeight(18)
            control_layout.addWidget(caption_label, 0, col)
            control_layout.addWidget(widget, 1, col)
            control_layout.setColumnStretch(col, 1)

        control_layout.setColumnMinimumWidth(4, 126)
        reset_btn = QPushButton("시뮬레이션 초기화")
        reset_btn.setMinimumHeight(36)
        control_layout.addWidget(
            reset_btn,
            1,
            4,
            1,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        simulation_widget = StressStrainSimulationWidget(self)
        simulation_widget.state_changed.connect(
            lambda payload, name=prefix: self._on_simulation_state_changed(name, payload)
        )

        layout.addWidget(info_scroll)
        layout.addWidget(control_card)
        layout.addWidget(simulation_widget, 1)

        setattr(self, f"{prefix}_simulation_status_label", status_label)
        setattr(self, f"{prefix}_simulation_detail_label", detail_label)
        setattr(self, f"{prefix}_simulation_assumption_label", assumption_label)
        setattr(self, f"{prefix}_simulation_control_card", control_card)
        setattr(self, f"{prefix}_simulation_gauge_spin", gauge_spin)
        setattr(self, f"{prefix}_simulation_width_spin", width_spin)
        setattr(self, f"{prefix}_simulation_thickness_spin", thickness_spin)
        setattr(self, f"{prefix}_simulation_area_value_label", area_value_label)
        setattr(self, f"{prefix}_simulation_reset_btn", reset_btn)
        setattr(self, f"{prefix}_simulation_widget", simulation_widget)

        self._simulation_status_labels.append(status_label)
        self._simulation_detail_labels.append(detail_label)
        self._simulation_assumption_labels.append(assumption_label)
        self._simulation_control_cards.append(control_card)
        self._simulation_reset_buttons.append(reset_btn)
        self._simulation_widgets.append(simulation_widget)

        for spin_box in [gauge_spin, width_spin, thickness_spin]:
            spin_box.valueChanged.connect(
                lambda _value, name=prefix: self._sync_simulation_assumptions(name, preserve_state=False)
            )
        reset_btn.clicked.connect(
            lambda _checked=False, name=prefix: getattr(self, f"{name}_simulation_widget").reset_simulation()
        )

        self._sync_simulation_assumptions(prefix, preserve_state=False)
        return tab

    def _on_simulation_state_changed(self, prefix, payload):
        status_label = getattr(self, f"{prefix}_simulation_status_label", None)
        detail_label = getattr(self, f"{prefix}_simulation_detail_label", None)
        assumption_label = getattr(self, f"{prefix}_simulation_assumption_label", None)
        if status_label is None or detail_label is None or assumption_label is None:
            return
        colors = self._theme()
        accent_color = payload.get("accent_color", colors["text_primary"])
        status_label.setText(payload.get("headline", ""))
        detail_label.setText(payload.get("detail", ""))
        assumption_label.setText(payload.get("assumption", ""))
        status_label.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {accent_color}; "
            f"background: {colors['muted_bg']}; border: 1px solid {colors['border']}; "
            "border-radius: 10px; padding: 12px 14px;"
        )
        current_strain = payload.get("current_strain", None)
        if current_strain is not None:
            self._update_stress_strain_marker(prefix, current_strain)

    def _update_stress_strain_marker(self, prefix, strain):
        canvas = getattr(self, "pretrained_curve_canvas" if prefix == "pretrained" else "stress_strain_canvas", None)
        if canvas is None or getattr(canvas, "_view_mode", None) != "curve":
            return
        ax = getattr(canvas, "axes", None)
        if ax is None:
            return

        for attr in ("_sim_marker_line", "_sim_marker_dot"):
            obj = getattr(canvas, attr, None)
            if obj is not None:
                try:
                    obj.remove()
                except Exception:
                    pass
            setattr(canvas, attr, None)

        if strain > 0 and hasattr(canvas, "_strain_data") and canvas._strain_data is not None:
            stress_at = float(np.interp(strain, canvas._strain_data, canvas._stress_data))
            canvas._sim_marker_line = ax.axvline(
                x=strain, color="#E56020", linestyle="--", linewidth=1.6, alpha=0.85, zorder=4
            )
            canvas._sim_marker_dot = ax.plot(
                strain, stress_at, "o", color="#E56020", markersize=8, zorder=6,
                markeredgecolor="white", markeredgewidth=1.5
            )[0]

        canvas.draw_idle()

    def _sync_simulation_assumptions(self, prefix, preserve_state=False):
        widget = getattr(self, f"{prefix}_simulation_widget", None)
        gauge_spin = getattr(self, f"{prefix}_simulation_gauge_spin", None)
        width_spin = getattr(self, f"{prefix}_simulation_width_spin", None)
        thickness_spin = getattr(self, f"{prefix}_simulation_thickness_spin", None)
        area_label = getattr(self, f"{prefix}_simulation_area_value_label", None)
        if (
            widget is None
            or gauge_spin is None
            or width_spin is None
            or thickness_spin is None
            or area_label is None
        ):
            return
        area_value = width_spin.value() * thickness_spin.value()
        area_label.setText(f"{area_value:.2f}")
        widget.set_assumptions(
            gauge_spin.value(),
            width_spin.value(),
            thickness_spin.value(),
            preserve_state=bool(preserve_state and widget.has_profile()),
        )

    def _render_simulation_view(self, prefix, mean, input_dict):
        widget = getattr(self, f"{prefix}_simulation_widget", None)
        if widget is None:
            return
        strain, stress, _, meta, _ = self._build_stress_strain_profile(mean, input_dict)
        widget.set_profile(strain, stress, meta)
        self._sync_simulation_assumptions(prefix, preserve_state=True)

    def _refresh_prediction_views_for_theme(self):
        if hasattr(self, "pretrained_prediction_canvas"):
            if self._pretrained_prediction_state:
                state = self._pretrained_prediction_state
                self._render_prediction_chart(
                    self.pretrained_prediction_canvas,
                    state["mean"],
                    state["std"],
                )
                self._render_stress_strain_curve(
                    self.pretrained_curve_canvas,
                    self.pretrained_curve_placeholder,
                    state["mean"],
                    state["input_dict"],
                )
            else:
                if getattr(self.pretrained_prediction_canvas, "_view_mode", None) == "placeholder":
                    self.render_prediction_placeholder(
                        self.pretrained_prediction_canvas,
                        "사전학습 예측 결과",
                        title_fontsize=12.5,
                        body_fontsize=9.8,
                    )
                if getattr(self.pretrained_curve_canvas, "_view_mode", None) == "placeholder":
                    self.render_stress_strain_placeholder(
                        self.pretrained_curve_canvas,
                        self.pretrained_curve_placeholder,
                    )

        if hasattr(self, "prediction_canvas"):
            if self._user_prediction_state:
                state = self._user_prediction_state
                self._render_prediction_chart(
                    self.prediction_canvas,
                    state["mean"],
                    state["std"],
                )
                self._render_stress_strain_curve(
                    self.stress_strain_canvas,
                    self.stress_strain_placeholder_label,
                    state["mean"],
                    state["input_dict"],
                )
            else:
                if getattr(self.prediction_canvas, "_view_mode", None) == "placeholder":
                    self.render_prediction_placeholder(
                        self.prediction_canvas,
                        "물성 예측 결과",
                        title_fontsize=11.4,
                        body_fontsize=9.0,
                    )
                if getattr(self.stress_strain_canvas, "_view_mode", None) == "placeholder":
                    self.render_stress_strain_placeholder(
                        self.stress_strain_canvas,
                        self.stress_strain_placeholder_label,
                    )

        for prefix in ["pretrained", "user"]:
            widget = getattr(self, f"{prefix}_simulation_widget", None)
            if widget is not None:
                widget.emit_current_state()

    def render_prediction_placeholder(self, canvas, title, title_fontsize=12.0, body_fontsize=9.5):
        colors = self._theme()
        canvas.fig.clear()
        ax = canvas.fig.add_subplot(111)
        canvas.axes = ax
        canvas._view_mode = "placeholder"
        ax.axis("off")
        ax.set_facecolor(colors["panel_bg"])
        canvas.fig.patch.set_facecolor(colors["panel_bg"])
        ax.text(
            0.5, 0.58,
            f"{title} 그래프가 여기에 표시됩니다.",
            ha="center", va="center",
            fontsize=title_fontsize,
            color=colors["text_sec"],
            transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.42,
            "예측을 실행하면 물성 요약 그래프가 자동으로 갱신됩니다.",
            ha="center", va="center",
            fontsize=body_fontsize,
            color=colors["text_label"],
            transform=ax.transAxes,
        )
        try:
            canvas.fig.tight_layout(pad=0.4)
        except Exception:
            pass
        canvas.draw()

    def render_stress_strain_placeholder(self, canvas, label, title_fontsize=14.0, body_fontsize=11.8):
        colors = self._theme()
        label.setText(
            "예측을 실행하면 yield stress, UTS, elongation, area reduction으로 근사한 "
            "engineering stress-strain curve가 여기에 표시됩니다."
        )
        canvas.fig.clear()
        ax = canvas.fig.add_subplot(111)
        canvas.axes = ax
        canvas._view_mode = "placeholder"
        ax.axis("off")
        ax.set_facecolor(colors["panel_bg"])
        canvas.fig.patch.set_facecolor(colors["panel_bg"])
        ax.text(
            0.5, 0.56,
            "Stress-Strain Curve preview",
            ha="center", va="center",
            fontsize=title_fontsize,
            color=colors["text_sec"],
            transform=ax.transAxes,
        )
        ax.text(
            0.5, 0.40,
            "탄성 구간, 항복점, 가공경화, necking 이후 파단 구간을 함께 표시합니다.",
            ha="center", va="center",
            fontsize=body_fontsize,
            color=colors["text_label"],
            transform=ax.transAxes,
        )
        try:
            canvas.fig.tight_layout(pad=0.4)
        except Exception:
            pass
        canvas.draw()

    def _style_prediction_axes(self, ax, title=None, xlabel=None, ylabel=None):
        colors = self._theme()
        ax.set_facecolor(colors["panel_bg"])
        ax.figure.patch.set_facecolor(colors["panel_bg"])
        ax.grid(True, color=colors["divider"], alpha=0.28, linewidth=0.8)
        for spine in ax.spines.values():
            spine.set_color(colors["border"])
        ax.tick_params(axis="both", colors=colors["text_sec"], labelcolor=colors["text_sec"])
        if title:
            ax.set_title(title, color=colors["text_primary"], fontsize=13, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel, color=colors["text_sec"])
        if ylabel:
            ax.set_ylabel(ylabel, color=colors["text_sec"])

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _estimate_elastic_modulus(self, temperature_k):
        temperature_k = self._safe_float(temperature_k, 293.15)
        temperature_c = temperature_k - 273.15
        softening_factor = 1.0 - max(0.0, temperature_c - 20.0) * 0.00022
        return float(np.clip(193000.0 * softening_factor, 125000.0, 210000.0))

    def _build_stress_strain_profile(self, mean, input_dict):
        from scipy.interpolate import PchipInterpolator

        yield_stress = max(self._safe_float(mean[0]), 1.0)
        uts = max(self._safe_float(mean[1], yield_stress + 1.0), yield_stress + 1.0)
        elongation_pct = float(np.clip(self._safe_float(mean[2], 2.0), 2.0, 120.0))
        area_reduction_pct = float(np.clip(self._safe_float(mean[3], 0.0), 0.0, 95.0))
        fracture_strain = max(elongation_pct / 100.0, 0.02)

        elastic_modulus = self._estimate_elastic_modulus(input_dict.get("Temperature (K)", 293.15))
        # physical yield strain (kept for metadata/labels)
        yield_strain = float(
            np.clip((yield_stress / elastic_modulus) + 0.002, 0.002, max(0.012, fracture_strain * 0.22))
        )
        if fracture_strain <= yield_strain + 0.01:
            fracture_strain = yield_strain + 0.01

        # display-only yield strain: elastic region visibility (not physical)
        display_yield_strain = float(max(yield_strain, 0.05 * fracture_strain))
        display_yield_strain = float(min(display_yield_strain, fracture_strain * 0.10))

        necking_ratio = 0.52 + 0.18 * (area_reduction_pct / 100.0)
        uts_strain = display_yield_strain + (fracture_strain - display_yield_strain) * necking_ratio
        uts_strain = float(np.clip(uts_strain, display_yield_strain + 0.006, fracture_strain - 0.003))
        if uts_strain >= fracture_strain:
            fracture_strain = uts_strain + 0.003

        fracture_stress_ratio = float(np.clip(0.80 - 0.42 * (area_reduction_pct / 100.0), 0.30, 0.80))
        fracture_stress = uts * fracture_stress_ratio

        # ── Region A: Elastic — strictly linear (display_yield_strain) ──────
        elastic_slope = yield_stress / max(display_yield_strain, 1e-6)
        elastic_x = np.linspace(0.0, display_yield_strain, 60)
        elastic_y = elastic_slope * elastic_x

        # ── Region B: Strain Hardening — PCHIP, concave-down ─────────────────
        # rapid initial hardening, gradual saturation near UTS
        h_t     = np.array([0.0, 0.18, 0.42, 0.68, 0.86, 1.0])
        h_shape = np.array([0.0, 0.46, 0.74, 0.91, 0.97, 1.0])  # concave-down fractions
        h_x = display_yield_strain + h_t * (uts_strain - display_yield_strain)
        h_y = yield_stress + (uts - yield_stress) * h_shape
        pchip_h = PchipInterpolator(h_x, h_y)
        hardening_x = np.linspace(display_yield_strain, uts_strain, 120)
        hardening_y = np.clip(pchip_h(hardening_x), yield_stress, uts)

        # ── Region C: Necking — PCHIP, accelerating drop (per spec) ──────────
        # minimal drop immediately after UTS, increasing rate toward fracture
        n_t     = np.array([0.0, 0.12, 0.32, 0.58, 0.82, 1.0])
        n_shape = np.array([0.0, 0.015, 0.105, 0.34, 0.68, 1.0])
        n_x = uts_strain + n_t * (fracture_strain - uts_strain)
        n_y = uts - (uts - fracture_stress) * n_shape
        pchip_n = PchipInterpolator(n_x, n_y)
        necking_x = np.linspace(uts_strain, fracture_strain, 80)
        necking_y = np.clip(pchip_n(necking_x), fracture_stress * 0.95, uts)

        strain = np.concatenate([elastic_x, hardening_x[1:], necking_x[1:]])
        stress = np.concatenate([elastic_y, hardening_y[1:], necking_y[1:]])
        segments = {
            "elastic":   (elastic_x, elastic_y),
            "hardening": (hardening_x, hardening_y),
            "necking":   (necking_x, necking_y),
        }
        points = {
            "Yield":    (display_yield_strain, yield_stress),
            "UTS":      (uts_strain,           uts),
            "Fracture": (fracture_strain,      fracture_stress),
        }
        meta = {
            "yield_stress":        yield_stress,
            "uts":                 uts,
            "elongation_pct":      elongation_pct,
            "area_reduction_pct":  area_reduction_pct,
            "elastic_modulus_gpa": elastic_modulus / 1000.0,
            "yield_strain":        yield_strain,          # physical (for info text)
            "uts_strain":          uts_strain,
            "fracture_strain":     fracture_strain,
        }
        return strain, stress, points, meta, segments

    def _render_stress_strain_curve(self, canvas, label, mean, input_dict):
        strain, stress, points, meta, segments = self._build_stress_strain_profile(mean, input_dict)

        canvas.fig.clear()
        ax = canvas.fig.add_subplot(111)
        canvas.axes = ax
        canvas._view_mode = "curve"
        self._style_prediction_axes(
            ax,
            title="Predicted Engineering Stress-Strain Curve",
            xlabel="Strain",
            ylabel="Stress (MPa)",
        )

        from matplotlib.transforms import blended_transform_factory
        dark = getattr(self, "_dark_mode", False)
        colors = self._theme()

        yield_x   = points["Yield"][0]
        yield_y   = points["Yield"][1]
        uts_x     = points["UTS"][0]
        uts_y     = points["UTS"][1]
        fracture_x = points["Fracture"][0]
        max_stress = max(float(np.max(stress)), meta["uts"])

        seg_colors = {
            "elastic":   "#2B5BA8" if dark else "#1D4E89",
            "hardening": "#B8690E" if dark else "#92400E",
            "necking":   "#9B1C1C" if dark else "#7F1D1D",
        }
        pt_colors = {
            "Yield":    seg_colors["elastic"],
            "UTS":      seg_colors["necking"],
            "Fracture": "#1A7A4A" if dark else "#14532D",
        }
        ref_col = "#555555" if dark else "#9CA3AF"
        ann_bg  = colors["panel_bg"]

        # minor grid
        ax.minorticks_on()
        ax.grid(True, which="minor", color=colors["divider"], alpha=0.20, linewidth=0.3, linestyle=":")

        # 구간 배경
        ax.axvspan(0.0,     yield_x,   color=seg_colors["elastic"],   alpha=0.05 if dark else 0.04)
        ax.axvspan(yield_x, uts_x,     color=seg_colors["hardening"], alpha=0.05 if dark else 0.04)
        ax.axvspan(uts_x,   fracture_x, color=seg_colors["necking"],  alpha=0.04 if dark else 0.03)

        # 인성 면적 (중립 회색)
        ax.fill_between(strain, stress,
                        color="#6B7280" if dark else "#9CA3AF",
                        alpha=0.10 if dark else 0.07, zorder=1)

        # 기준선
        ax.axvline(yield_x, color=ref_col, linewidth=0.8, linestyle="--", alpha=0.55, zorder=2)
        ax.axvline(uts_x,   color=ref_col, linewidth=0.8, linestyle="--", alpha=0.45, zorder=2)
        ax.axhline(yield_y, color=ref_col, linewidth=0.7, linestyle=":",  alpha=0.45, zorder=2)

        # 곡선
        for segment_name, (x_vals, y_vals) in segments.items():
            ax.plot(x_vals, y_vals, color=seg_colors[segment_name],
                    linewidth=2.2, solid_capstyle="butt", zorder=3)

        # 구간 레이블 (상단 고정, 화살표 없음)
        trans = blended_transform_factory(ax.transData, ax.transAxes)
        zone_info = [
            ("Elastic",           (0.0 + yield_x) / 2,    seg_colors["elastic"]),
            ("Plastic hardening", (yield_x + uts_x) / 2,  seg_colors["hardening"]),
            ("Necking",           (uts_x + fracture_x) / 2, seg_colors["necking"]),
        ]
        for zlabel, xc, zc in zone_info:
            ax.text(xc, 0.975, zlabel, transform=trans,
                    fontsize=8, color=zc, ha="center", va="top", fontweight="600",
                    bbox=dict(boxstyle="square,pad=0.15", fc=ann_bg, ec="none", alpha=0.70))

        # 주요 점 annotation
        offsets = {"Yield": (10, 40), "UTS": (-72, -38), "Fracture": (-84, -8)}
        for name, (x_val, y_val) in points.items():
            c = pt_colors[name]
            ax.scatter([x_val], [y_val], s=30, color=c, zorder=5, linewidths=0)
            ax.annotate(
                f"{name}\n({x_val:.3f},  {y_val:.0f} MPa)",
                xy=(x_val, y_val), xytext=offsets[name],
                textcoords="offset points", fontsize=8.5,
                color=c, fontweight="bold",
                bbox=dict(boxstyle="square,pad=0.18", fc=ann_bg, ec="none", alpha=0.88),
                arrowprops={"arrowstyle": "-", "color": c, "lw": 0.8},
            )

        ax.set_xlim(0.0, max(fracture_x * 1.08, 0.02))
        ax.set_ylim(0.0, max_stress * 1.20)
        try:
            canvas.fig.tight_layout(pad=0.4)
        except Exception:
            pass
        canvas._strain_data = strain
        canvas._stress_data = stress
        canvas._sim_marker_line = None
        canvas._sim_marker_dot = None
        canvas.draw()

        label.setText(
            "예측 물성으로 근사한 engineering stress-strain curve입니다. "
            f"Yield {meta['yield_stress']:.1f} MPa, UTS {meta['uts']:.1f} MPa, "
            f"Elongation {meta['elongation_pct']:.1f}%, Area reduction {meta['area_reduction_pct']:.1f}% "
            f"(탄성계수 추정 {meta['elastic_modulus_gpa']:.1f} GPa). "
            "실험 인장시험 곡선이 아니라 경향 확인용 그래프입니다."
        )

    def _render_prediction_chart(self, canvas, mean, std):
        canvas.fig.clear()
        ax1 = canvas.fig.add_subplot(111)
        canvas.axes = ax1
        canvas._view_mode = "prediction"
        labels = ["Yield", "UTS", "Elong.", "Area Red."]
        x = np.arange(len(labels))
        colors = self._theme()

        self._style_prediction_axes(ax1, title="예측 물성 결과")
        ax1.grid(False)

        stress_vals = [mean[0], mean[1], 0, 0]
        stress_errs = [1.96 * std[0], 1.96 * std[1], 0, 0]
        ax1.bar(x[:2], stress_vals[:2], yerr=stress_errs[:2], capsize=10, color=["#3498db", "#e74c3c"])
        ax1.set_ylabel("Stress (MPa)", color=colors["text_sec"])
        ax1.tick_params(axis="y", colors=colors["text_sec"])

        ax2 = ax1.twinx()
        ax2.set_facecolor("none")
        duct_vals = [0, 0, mean[2], mean[3]]
        duct_errs = [0, 0, 1.96 * std[2], 1.96 * std[3]]
        ax2.bar(x[2:], duct_vals[2:], yerr=duct_errs[2:], capsize=10, color=["#2ecc71", "#f39c12"])
        ax2.set_ylabel("Percentage (%)", color=colors["text_sec"])
        ax2.tick_params(axis="y", colors=colors["text_sec"])
        for spine in ax2.spines.values():
            spine.set_color(colors["border"])

        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        ax1.tick_params(axis="x", colors=colors["text_sec"])
        try:
            canvas.fig.tight_layout(pad=0.4)
        except Exception:
            pass
        canvas.draw()

    def _open_strain_explore_dialog(self, prefix: str):
        if prefix == "pretrained":
            model_engine = getattr(self, "pretrained_model_engine", None)
            data_engine = getattr(self, "pretrained_data_engine", None)
            state = getattr(self, "_pretrained_prediction_state", None)
        else:
            model_engine = getattr(self, "model_engine", None)
            data_engine = getattr(self, "data_engine", None)
            state = getattr(self, "_user_prediction_state", None)

        if not model_engine or not data_engine:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "모델 없음",
                "먼저 예측을 실행한 뒤 자세하게 보기를 사용할 수 있습니다.",
            )
            return

        if not state or not state.get("input_dict"):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "예측 필요",
                "먼저 예측을 실행한 뒤 자세하게 보기를 사용할 수 있습니다.",
            )
            return

        base_input = dict(state["input_dict"])

        dlg = StrainExploreDialog(model_engine, data_engine, base_input, self._build_stress_strain_profile, self)
        dlg.show()

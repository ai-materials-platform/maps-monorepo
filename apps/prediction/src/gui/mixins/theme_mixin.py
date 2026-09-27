from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QDoubleSpinBox, QLabel

from src.gui.constants import DARK_QSS, LIGHT_QSS


class ThemeMixin:
    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._theme_btn.setText("라이트 모드" if self._dark_mode else "다크 모드")
        qss = DARK_QSS if self._dark_mode else LIGHT_QSS
        QApplication.instance().setStyleSheet(qss)
        self.setStyleSheet(qss)
        self._apply_theme_colors()
        if hasattr(self, "canvas"):
            if self.last_r2_avg is None:
                self.render_training_placeholder()
            elif hasattr(self, "_last_metrics"):
                self._render_training_bar_chart(self._last_metrics)
        if hasattr(self, "perf_canvas"):
            if self.last_r2_avg is None:
                self.render_performance_placeholder()
            elif hasattr(self, "_last_training_results"):
                self.render_performance_results(self._last_training_results)

    def _theme(self):
        d = self._dark_mode
        return {
            "app_bg":      "#1E1E1E" if d else "#F4F6F8",
            "panel_bg":    "#252526" if d else "#FFFFFF",
            "muted_bg":    "#2D2D2D" if d else "#F8FAFC",
            "info_bg":     "#2D2D2D" if d else "#F6F8FB",
            "divider":     "#3E3E42" if d else "#CBD5E1",
            "border":      "#3E3E42" if d else "#C9D2DC",
            "text_primary":"#D4D4D4" if d else "#111827",
            "text_sec":    "#CCCCCC" if d else "#334155",
            "text_label":  "#9D9D9D" if d else "#64748B",
            "tb_bg":       "#1E1E1E" if d else "#FFFFFF",
            "tb_border":   "#3E3E42" if d else "#C9D2DC",
            "status_bg":   "#1E1E1E" if d else "#FFFFFF",
            "status_text": "#D4D4D4" if d else "#111827",
            "status_muted":"#9D9D9D" if d else "#334155",
            "input_bg":    "#3C3C3C" if d else "#FFFFFF",
            "accent":      "#1E293B",
        }

    def _apply_theme_colors(self):
        c = self._theme()

        palette = QPalette()
        if self._dark_mode:
            palette.setColor(QPalette.ColorRole.Window,          QColor("#1E1E1E"))
            palette.setColor(QPalette.ColorRole.WindowText,      QColor("#D4D4D4"))
            palette.setColor(QPalette.ColorRole.Base,            QColor("#252526"))
            palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#1E1E1E"))
            palette.setColor(QPalette.ColorRole.Text,            QColor("#D4D4D4"))
            palette.setColor(QPalette.ColorRole.Button,          QColor("#2D2D2D"))
            palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#D4D4D4"))
            palette.setColor(QPalette.ColorRole.Highlight,       QColor("#264F78"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#252526"))
            palette.setColor(QPalette.ColorRole.ToolTipText,     QColor("#D4D4D4"))
        else:
            palette.setColor(QPalette.ColorRole.Window,          QColor("#F2F2F0"))
            palette.setColor(QPalette.ColorRole.WindowText,      QColor("#1A1A1A"))
            palette.setColor(QPalette.ColorRole.Base,            QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#F8F8F7"))
            palette.setColor(QPalette.ColorRole.Text,            QColor("#1A1A1A"))
            palette.setColor(QPalette.ColorRole.Button,          QColor("#EBEBEA"))
            palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#1A1A1A"))
            palette.setColor(QPalette.ColorRole.Highlight,       QColor("#1E293B"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        QApplication.instance().setPalette(palette)

        self._toolbar_widget.setStyleSheet(
            f"background: {c['tb_bg']}; border-bottom: 1px solid {c['tb_border']};"
        )
        if hasattr(self, "_toolbar_title"):
            self._toolbar_title.setStyleSheet(
                f"color: {'#F8FAFC' if self._dark_mode else '#111827'}; font-size: 15px; font-weight: 700; letter-spacing: 0.2px;"
            )
        if hasattr(self, "_theme_btn"):
            self._theme_btn.setText("라이트 모드" if self._dark_mode else "다크 모드")
            theme_bg = "#FFFFFF" if self._dark_mode else "#111827"
            theme_text = "#111827" if self._dark_mode else "#F8FAFC"
            theme_border = c["border"] if self._dark_mode else "#111827"
            theme_hover = "#F8FAFC" if self._dark_mode else "#1F2937"
            theme_hover_border = "#CBD5E1" if self._dark_mode else "#334155"
            self._theme_btn.setStyleSheet(
                "QPushButton { "
                f"background: {theme_bg}; color: {theme_text}; border: 1px solid {theme_border}; "
                "border-radius: 16px; font-size: 11px; font-weight: 700; padding: 0 14px; }"
                f"QPushButton:hover {{ background: {theme_hover}; border-color: {theme_hover_border}; }}"
            )
        # 메뉴바 숨김 — 커스텀 타이틀바에 통합됨
        self.statusBar().setStyleSheet(
            f"QStatusBar {{ background: {c['status_bg']}; color: {c['status_text']}; font-size: 11px; "
            f"padding: 0 8px; border-top: 1px solid {c['border']}; }}"
            "QStatusBar::item { border: none; }"
        )

        for w in self._panel_widgets:
            w.setStyleSheet(f"background: {c['panel_bg']};")

        for w in self._panel_header_widgets:
            w.setStyleSheet(
                f"font-size: 11px; color: {c['text_label']}; padding: 10px 14px; "
                f"letter-spacing: 0.8px; font-weight: 600; border-bottom: 1px solid {c['divider']};"
            )

        for w in self._divider_widgets:
            w.setStyleSheet(f"background: {c['divider']};")

        for w in self._info_box_widgets:
            w.setStyleSheet(
                f"font-size: 12px; color: {c['text_sec']}; background: {c['info_bg']}; "
                f"padding: 10px; border-left: 3px solid {c['accent']}; border-radius: 6px;"
            )

        for w in self._section_lbl_widgets:
            w.setStyleSheet(
                f"font-size: 12px; color: {c['text_primary']}; font-weight: 700; "
                f"padding: 0 0 4px 0; border-bottom: 1px solid {c['divider']}; background: transparent;"
            )

        for w in self._muted_bg_widgets:
            w.setStyleSheet(
                f"font-size: 12px; color: {c['text_sec']}; padding: 10px; "
                f"background: {c['muted_bg']}; border: 1px solid {c['border']}; border-radius: 6px;"
            )

        self.file_path_label.setStyleSheet(f"font-size: 12px; color: {c['text_sec']};")
        self.status_label.setStyleSheet(f"color: {c['text_sec']}; font-size: 11px;")
        self.domain_range_status_label.setStyleSheet(f"color: {c['text_sec']}; font-size: 11px;")
        self.domain_rule_label.setStyleSheet(f"font-size: 11px; color: {c['text_label']}; background: transparent; padding: 0;")
        self.feature_engineering_label.setStyleSheet(f"font-size: 11px; color: {c['text_label']}; background: transparent; padding: 0;")
        self.quality_summary_label.setStyleSheet(f"font-size: 11px; color: {c['text_label']}; padding: 4px 0; background: transparent;")
        self.reset_preprocess_btn.setStyleSheet(
            f"QPushButton {{ background: {c['muted_bg']}; color: {c['text_sec']}; border: 1px solid {c['border']}; border-radius: 3px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: {c['border']}; }}"
        )

        self._sb_status.setStyleSheet(
            f"color: {c['accent'] if self.preprocessing_ready and not self.model_engine else '#58C472'}; "
            "font-size: 11px; font-weight: 700; padding: 0 10px;"
        )
        for lbl in [self._sb_samples, self._sb_missing, self._sb_model]:
            lbl.setStyleSheet(
                f"color: {c['status_muted']}; font-size: 11px; font-weight: 600; padding: 0 10px;"
            )

        for w in self._tree_section_title_lbls:
            w.setStyleSheet(
                f"font-size: 11px; color: {c['text_label']}; font-weight: 700; letter-spacing: 0.4px;"
            )

        # ── 다크모드 전용 위젯 오버라이드 ────────────────────────────────────
        if self._dark_mode:
            # 파일 열기 버튼
            self.select_file_btn.setStyleSheet(
                "QPushButton { background: #2D2D2D; color: #D4D4D4; border: 1px solid #3E3E42; "
                "border-radius: 3px; font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { background: #3A3A3A; border-color: #5A5A5A; }"
                "QPushButton:pressed { background: #252526; }"
            )
            # 전처리 실행 버튼
            self.preprocess_btn.setStyleSheet(
                "QPushButton { background: #3A3A3A; color: #D4D4D4; border: none; "
                "border-radius: 3px; font-size: 12px; font-weight: 700; }"
                "QPushButton:hover { background: #4A4A4A; }"
                "QPushButton:disabled { background: #2D2D2D; color: #5A5A5A; }"
            )
            # 학습 버튼
            self.train_btn.setStyleSheet(
                "QPushButton { background: #1D4ED8; color: #EFF6FF; border: none; "
                "border-radius: 3px; font-size: 12px; font-weight: 700; }"
                "QPushButton:hover { background: #2563EB; }"
                "QPushButton:disabled { background: #1E3355; color: #4B6080; }"
            )
            # 학습 도움말 라벨 (파란 info box → 일반 텍스트)
            if hasattr(self, "_training_help_label"):
                self._training_help_label.setStyleSheet(
                    "font-size: 11px; color: #94A3B8; font-weight: 600; "
                    "background: transparent; padding: 2px 0; border: none;"
                )
            # 도메인/합금 설명 + 전처리 요약 (이미 transparent이지만 색상 재보장)
            self.domain_rule_label.setStyleSheet(
                f"font-size: 11px; color: {c['text_label']}; background: transparent; padding: 0;"
            )
            self.feature_engineering_label.setStyleSheet(
                f"font-size: 11px; color: {c['text_label']}; background: transparent; padding: 0;"
            )

        info_bg = "#15324A" if self._dark_mode else "#EFF6FF"
        info_border = "#1E293B" if self._dark_mode else "#BFDBFE"
        info_text = "#DBEAFE" if self._dark_mode else "#1D4ED8"
        warn_bg = "#4A3818" if self._dark_mode else "#FFF7D6"
        warn_border = "#D4A72C" if self._dark_mode else "#FACC15"
        warn_text = "#FDE68A" if self._dark_mode else "#7A5D00"
        success_bg = "#173B2F" if self._dark_mode else "#ECFDF3"
        success_border = "#22C55E" if self._dark_mode else "#86EFAC"
        success_text = "#DCFCE7" if self._dark_mode else "#166534"

        if hasattr(self, "processed_preview_info_label"):
            self.processed_preview_info_label.setStyleSheet(
                f"font-size: 11px; color: {c['text_sec']}; padding: 8px 10px; "
                f"background: {c['muted_bg']}; border-top: 1px solid {c['divider']};"
            )
        if self._prediction_input_groups or self._prediction_input_fields or self._prediction_input_labels:
            self._apply_prediction_input_styles()
        if hasattr(self, "_quality_delegate"):
            self._quality_delegate.dark_mode = self._dark_mode
        _export_btn_style = (
            f"QPushButton {{ background: transparent; color: {c['text_label']}; "
            f"border: 1px solid {c['border']}; border-radius: 6px; "
            "font-size: 11px; font-weight: 600; padding: 0 12px; }"
            f"QPushButton:hover {{ background: {c['muted_bg']}; }}"
            f"QPushButton:disabled {{ color: {c['border']}; }}"
        )
        for btn_attr in ("pretrained_export_btn", "user_export_btn"):
            if hasattr(self, btn_attr):
                getattr(self, btn_attr).setStyleSheet(_export_btn_style)
        from PyQt6.QtWidgets import QLabel as _QLabel
        title_color = "#F3F4F6" if self._dark_mode else "#111827"
        sub_color = "#94A3B8" if self._dark_mode else "#64748B"
        for card_attr in ("austenite_domain_btn", "high_temp_domain_btn"):
            if hasattr(self, card_attr):
                card = getattr(self, card_attr)
                card_bg = "#252526" if self._dark_mode else "#FFFFFF"
                card_border = "#3E3E42" if self._dark_mode else "#C9D2DC"
                card_hover = "#2D2D2D" if self._dark_mode else "#F1F5F9"
                card.setStyleSheet(
                    f"QWidget {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 10px; }}"
                    f"QWidget:hover {{ background: {card_hover}; border-color: #1E293B; }}"
                )
                labels = card.findChildren(_QLabel)
                if len(labels) >= 1:
                    labels[0].setStyleSheet(f"font-size: 12px; font-weight: 700; color: {title_color}; border: none; background: transparent;")
                if len(labels) >= 2:
                    labels[1].setStyleSheet(f"font-size: 10px; color: {sub_color}; border: none; background: transparent;")
        if hasattr(self, "feature_selection_status_label"):
            self.feature_selection_status_label.setStyleSheet(
                f"font-size: 11px; font-weight: 600; color: {c['text_primary']}; "
                "background: transparent; padding: 2px 0; border: none;"
            )
        if hasattr(self, "training_data_status_label"):
            self.training_data_status_label.setStyleSheet(
                f"font-size: 11px; font-weight: 600; color: {c['text_primary']}; "
                "background: transparent; padding: 2px 0; border: none;"
            )
        if hasattr(self, "active_model_info"):
            card_bg = success_bg if self.model_engine else info_bg
            card_border = success_border if self.model_engine else info_border
            card_text = success_text if self.model_engine else info_text
            self.active_model_info.setStyleSheet(
                f"background-color: {card_bg}; color: {card_text}; padding: 11px 12px; "
                f"border: 1px solid {card_border}; border-radius: 10px; font-weight: 700; margin-bottom: 12px;"
            )
        for attr_name in ["result_display", "pretrained_result_display"]:
            if hasattr(self, attr_name):
                getattr(self, attr_name).setStyleSheet(
                    f"font-size: 12px; font-weight: 600; color: {c['text_primary']}; "
                    f"background: {c['muted_bg']}; border: 1px solid {c['border']}; "
                    "border-radius: 10px; padding: 12px;"
                )
        for panel in self._curve_info_panels:
            panel.setStyleSheet(
                f"background: {c['muted_bg']}; border: 1px solid {c['border']}; border-radius: 10px;"
            )
        for attr_name in ["pretrained_curve_placeholder", "stress_strain_placeholder_label"]:
            if hasattr(self, attr_name):
                getattr(self, attr_name).setStyleSheet(
                    f"font-size: 13px; font-weight: 600; color: {c['text_sec']}; "
                    "background: transparent; border: none; padding: 4px 0 0 0;"
                )
        for label in self._simulation_detail_labels:
            label.setStyleSheet(
                f"font-size: 12px; color: {c['text_sec']}; "
                "background: transparent; border: none; padding: 2px 8px 0 8px;"
            )
        for label in self._simulation_assumption_labels:
            label.setStyleSheet(
                f"font-size: 11px; color: {c['text_label']}; "
                "background: transparent; border: none; padding: 0 8px 2px 8px;"
            )
        for card in self._simulation_control_cards:
            card.setStyleSheet(
                f"background: {c['muted_bg']}; border: 1px solid {c['border']}; border-radius: 10px;"
            )
            for label in card.findChildren(QLabel):
                if label.property("simulation_role") == "caption":
                    label.setStyleSheet(
                        f"font-size: 11px; font-weight: 700; color: {c['text_sec']}; "
                        "background: transparent; border: none; padding: 0 0 2px 0;"
                    )
                else:
                    label.setStyleSheet(
                        f"font-size: 11px; font-weight: 600; color: {c['text_sec']}; "
                        f"background: {c['panel_bg']}; border: 1px solid {c['border']}; "
                        "border-radius: 8px; padding: 7px 10px; min-height: 20px;"
                    )
            for spin_box in card.findChildren(QDoubleSpinBox):
                spin_box.setStyleSheet(
                    "QDoubleSpinBox { "
                    f"background: {c['input_bg']}; color: {c['text_primary']}; border: 1px solid {c['border']}; "
                    "border-radius: 8px; padding: 7px 10px; min-height: 20px; }"
                    "QDoubleSpinBox:focus { border-color: #1E293B; }"
                )
        for button in self._simulation_reset_buttons:
            button.setStyleSheet(
                "QPushButton { background: #1E293B; color: white; border: none; border-radius: 9px; "
                "font-weight: 700; padding: 8px 14px; }"
                "QPushButton:hover { background: #334155; }"
            )
        for widget in self._simulation_widgets:
            widget.set_theme(c, self._dark_mode)
        legend_bg = "#FFFFFF" if not self._dark_mode else "#252526"
        legend_border = "#CBD5E1" if not self._dark_mode else "#3E3E42"
        legend_text = "#334155" if not self._dark_mode else "#D4D4D4"
        for card in self._curve_legend_cards:
            card.setStyleSheet(
                f"background: {legend_bg}; border: 1px solid {legend_border}; border-radius: 8px;"
            )
        for label in self._curve_legend_label_widgets:
            label.setStyleSheet(
                f"font-size: 11px; font-weight: 600; color: {legend_text}; "
                "background: transparent; border: none;"
            )
        if hasattr(self, "comp_group_title_label"):
            self.comp_group_title_label.setStyleSheet(
                f"font-size: 14px; font-weight: 700; color: {c['text_primary']}; padding: 0 2px 4px 2px;"
            )
        if hasattr(self, "proc_group_title_label"):
            self.proc_group_title_label.setStyleSheet(
                f"font-size: 14px; font-weight: 700; color: {c['text_primary']}; padding: 0 2px 4px 2px;"
            )
        if hasattr(self, "inference_tab"):
            self.inference_tab.setStyleSheet(f"background: {c['app_bg']};")
        if hasattr(self, "material_prediction_page"):
            self.material_prediction_page.setStyleSheet(f"background: {c['app_bg']};")
        if hasattr(self, "user_page"):
            self.user_page.setStyleSheet(f"background: {c['app_bg']};")
        if hasattr(self, "main_mode_stack"):
            self.main_mode_stack.setStyleSheet(f"background: {c['app_bg']};")
        if hasattr(self, "_mp_prediction_guide_corner"):
            tab_bg = "#1E1E1E" if self._dark_mode else "#E9EEF3"
            self._mp_prediction_guide_corner.setStyleSheet(
                f"background: {tab_bg}; border: none;"
            )
        if hasattr(self, "_mp_prediction_guide_btn"):
            self._mp_prediction_guide_btn.setStyleSheet(
                "QPushButton { background: #EEF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; "
                "border-radius: 14px; font-size: 11px; font-weight: 700; padding: 0 14px; }"
                "QPushButton:hover { background: #DBEAFE; }"
            )
        if hasattr(self, "inference_left_frame"):
            self.inference_left_frame.setStyleSheet(
                f"background: {c['panel_bg']}; border: 1px solid {c['border']}; border-radius: 12px;"
            )
        if hasattr(self, "inference_right_frame"):
            self.inference_right_frame.setStyleSheet(
                f"background: {c['panel_bg']}; border: 1px solid {c['border']}; border-radius: 12px;"
            )
        if hasattr(self, "perf_header_label"):
            self.perf_header_label.setStyleSheet(
                f"font-size: 16px; font-weight: 700; color: {c['text_primary']};"
            )
        if hasattr(self, "perf_desc_label"):
            self.perf_desc_label.setStyleSheet(
                f"color: {c['text_sec']}; font-weight: 600;"
            )
        if hasattr(self, "ws_header"):
            self.ws_header.setStyleSheet(
                f"background: {c['panel_bg']}; border-bottom: 1px solid {c['divider']};"
            )
        if hasattr(self, "ws_title_label"):
            self.ws_title_label.setStyleSheet(
                f"font-size: 18px; font-weight: 700; color: {c['text_primary']};"
            )
        if hasattr(self, "ws_count_badge"):
            self.ws_count_badge.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: {c['text_label']};"
            )
        if hasattr(self, "ws_search_input"):
            self.ws_search_input.setStyleSheet(
                f"QLineEdit {{ background: {c['input_bg']}; color: {c['text_primary']}; "
                f"border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 10px; font-size: 12px; }}"
                f"QLineEdit:focus {{ border-color: #6366F1; background: {c['input_bg']}; }}"
            )
        if hasattr(self, "ws_new_save_btn"):
            btn_bg = "#E5E7EB" if self._dark_mode else "#111827"
            btn_text = "#111827" if self._dark_mode else "#F9FAFB"
            btn_hover = "#D1D5DB" if self._dark_mode else "#1F2937"
            self.ws_new_save_btn.setStyleSheet(
                f"QPushButton {{ background: {btn_bg}; color: {btn_text}; border: none; border-radius: 6px; "
                "font-weight: 700; font-size: 12px; }"
                f"QPushButton:hover {{ background: {btn_hover}; }}"
            )
        if hasattr(self, "ws_footer"):
            self.ws_footer.setStyleSheet(
                f"background: {c['panel_bg']}; border-top: 1px solid {c['divider']};"
            )
        if hasattr(self, "ws_rows_label"):
            self.ws_rows_label.setStyleSheet(f"font-size: 12px; color: {c['text_label']};")
        if hasattr(self, "ws_page_info_label"):
            self.ws_page_info_label.setStyleSheet(
                f"font-size: 12px; font-weight: 600; color: {c['text_sec']};"
            )
        for _btn_attr in ("ws_prev_page_btn", "ws_next_page_btn"):
            if hasattr(self, _btn_attr):
                getattr(self, _btn_attr).setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {c['text_sec']}; "
                    f"border: 1px solid {c['border']}; border-radius: 6px; font-size: 11px; }}"
                    f"QPushButton:hover {{ background: {c['muted_bg']}; }}"
                    f"QPushButton:disabled {{ color: {c['divider']}; border-color: {c['divider']}; }}"
                )
        if hasattr(self, "ws_table"):
            sel_bg = "#264F78" if self._dark_mode else "#EEF2FF"
            self.ws_table.setStyleSheet(
                f"QTableWidget {{ background: {c['panel_bg']}; border: none; outline: none; }}"
                f"QTableWidget::item {{ padding: 8px 12px; border-bottom: 1px solid {c['divider']}; color: {c['text_primary']}; }}"
                f"QTableWidget::item:selected {{ background: {sel_bg}; color: {c['text_primary']}; }}"
                f"QHeaderView::section {{ background: {c['muted_bg']}; color: {c['text_label']}; font-size: 11px; font-weight: 600; "
                f"padding: 8px 12px; border: none; border-bottom: 1px solid {c['divider']}; }}"
            )
        if hasattr(self, "_settings_scroll"):
            handle = "#4F5965" if self._dark_mode else "#CBD5E1"
            handle_hv = "#6B7280" if self._dark_mode else "#94A3B8"
            self._settings_scroll.setStyleSheet(
                "QScrollArea { background: transparent; border: none; }"
                f"QScrollBar:vertical {{ width: 6px; background: transparent; }}"
                f"QScrollBar::handle:vertical {{ background: {handle}; border-radius: 3px; min-height: 20px; }}"
                f"QScrollBar::handle:vertical:hover {{ background: {handle_hv}; }}"
                "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
                "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
            )
        if hasattr(self, "preprocessing_tab"):
            self.preprocessing_tab.setStyleSheet(f"background: {c['panel_bg']};")
        if hasattr(self, "workspace_tab"):
            self.workspace_tab.setStyleSheet(f"background: {c['panel_bg']};")
        if hasattr(self, "_settings_header_row"):
            self._settings_header_row.setStyleSheet(
                f"background: {c['panel_bg']}; border-bottom: 1px solid {c['divider']};"
            )
        if hasattr(self, "_settings_header_label"):
            self._settings_header_label.setStyleSheet(
                f"font-size: 11px; color: {c['text_label']}; padding: 10px 14px; "
                "letter-spacing: 0.8px; font-weight: 600;"
            )
        if hasattr(self, "_settings_help_btn"):
            self._settings_help_btn.setStyleSheet(
                "QPushButton { "
                f"background: transparent; color: {c['text_label']}; border: 1px solid {c['border']}; "
                "border-radius: 10px; font-size: 11px; font-weight: 700; padding: 0; margin: 4px 8px 4px 0; }"
                f"QPushButton:hover {{ background: {c['muted_bg']}; color: {c['text_primary']}; }}"
            )
        if hasattr(self, "ws_name_input"):
            self.ws_name_input.setStyleSheet(
                f"QLineEdit {{ background: {c['input_bg']}; color: {c['text_primary']}; "
                f"border: 1px solid {c['border']}; border-radius: 6px; padding: 6px 10px; }}"
            )
        if hasattr(self, "ws_combo"):
            self.ws_combo.setStyleSheet(
                f"QComboBox {{ background: {c['input_bg']}; color: {c['text_primary']}; "
                f"border: 1px solid {c['border']}; border-radius: 6px; padding: 5px 10px; }}"
            )
        if hasattr(self, "_tree_file_label"):
            self._update_project_tree()
        self._refresh_prediction_views_for_theme()
        if hasattr(self, "_apply_llm_chat_theme"):
            self._apply_llm_chat_theme()
        self._apply_mode_button_styles()
        # 커스텀 타이틀바 다크모드 업데이트
        if hasattr(self, "_custom_titlebar"):
            self._custom_titlebar.update()
            from PyQt6.QtWidgets import QToolButton  # noqa: PLC0415
            c = self._theme()
            for btn in self._custom_titlebar.findChildren(QToolButton):
                btn.setStyleSheet(
                    f"QToolButton{{background:transparent;color:{c['text_sec']};border:none;"
                    f"font-size:11px;font-weight:600;padding:4px 10px;border-radius:4px;}}"
                    f"QToolButton:hover{{background:{c['muted_bg']};color:{c['text_primary']};}}"
                    "QToolButton::menu-indicator{image:none;}"
                )

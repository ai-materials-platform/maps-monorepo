import os

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class PreprocessingMixin:
    def refresh_domain_range_status(self):
        custom_count = len(getattr(self.data_engine, "custom_ranges", {}))
        total_count = len(self.data_engine.get_domain_ranges())
        if custom_count:
            self.domain_range_status_label.setText(
                f"현재 사용자 지정 기준 {custom_count}개가 적용되어 있습니다. 검증 대상 컬럼은 총 {total_count}개입니다."
            )
        else:
            self.domain_range_status_label.setText(
                f"현재 기본 도메인 기준으로 검증합니다. 검증 대상 컬럼은 총 {total_count}개입니다."
            )

    def mark_preprocessing_dirty(self, *_args):
        self.preprocessing_ready = False
        self.train_btn.setEnabled(False)
        self.go_to_training_btn.setEnabled(False)
        if hasattr(self, "go_to_model_training_btn"):
            self.go_to_model_training_btn.setEnabled(False)
        if hasattr(self, "generate_features_btn"):
            self.generate_features_btn.setEnabled(False)
        if self.data_engine.df is not None and not self.data_engine.df.empty:
            self.training_data_status_label.setText("▲ 현재 결과는 이전 설정 기준입니다. 전처리를 다시 실행해 주세요.")
            self.training_status_label.setText("상태: 설정이 변경되어 학습이 잠시 비활성화되었습니다. 전처리를 다시 실행해 주세요.")
            self.quality_summary_label.setText("전처리 설정이 변경되었습니다. 현재 표는 이전 설정 기준 결과입니다.")
            self.processed_preview_info_label.setText("현재 표는 이전 전처리 결과입니다. 새 설정을 반영하려면 전처리를 다시 실행해 주세요.")
            return
        self.training_data_status_label.setText("")
        self.training_status_label.setText("")
        self.quality_summary_label.setText("전처리 설정이 변경되었습니다. 전처리를 다시 실행해 주세요.")
        self.processed_preview_info_label.setText("설정이 변경되었고 아직 전처리 결과가 없습니다. 전처리를 다시 실행해 주세요.")

        if hasattr(self, "feature_selection_status_label"):
            self.feature_selection_status_label.setText(
                "▲ 먼저 전처리를 실행한 뒤, 이 탭에서 학습 컬럼을 선택해 주세요."
            )

    def apply_quality_settings_from_ui(self):
        missing_map = {0: "mean", 1: "median", 2: "knn", 3: "drop"}
        outlier_map = {0: "clip", 1: "remove", 2: "flag"}
        invalid_type_map = {0: "coerce", 1: "drop"}
        self.data_engine.configure_quality_rules(
            missing_strategy=missing_map.get(self.missing_combo.currentIndex(), "mean"),
            outlier_strategy=outlier_map.get(self.outlier_combo.currentIndex(), "clip"),
            invalid_type_strategy=invalid_type_map.get(self.invalid_type_combo.currentIndex(), "coerce"),
            iqr_factor=self.iqr_spin.value(),
            input_feature_mode="combined",
        )

    def update_quality_summary_from_report(self, report):
        if not report:
            self.quality_summary_label.setText("전처리 결과 요약이 아직 없습니다.")
            self.domain_rule_label.setText("도메인 기준 검증 결과가 아직 없습니다.")
            return

        self.quality_summary_label.setText(
            "데이터 품질 처리 결과: "
            f"행 {report.get('rows_before', 0)} -> {report.get('rows_after', 0)}, "
            f"형식 오류 {report.get('invalid_type_cells', 0)}개, "
            f"누락값 {report.get('missing_cells_before', 0)} -> {report.get('missing_cells_after', 0)}, "
            f"이상치 감지 {report.get('outlier_cells', 0)}개, "
            f"합금 지표 생성 {len(report.get('engineered_features_added', []))}개"
        )
        self.domain_rule_label.setText(
            "도메인 기준 검증 결과: "
            f"{report.get('domain_range_cells', 0)}개의 값이 설정 범위를 벗어났습니다."
        )

    def populate_processed_preview(self, df):
        base_df = self.data_engine.get_preprocessed_display_df()
        engineered_df = self.data_engine.get_engineered_display_df()
        self.processed_preview_table.clear()
        self.processed_preview_table.setRowCount(len(base_df))
        self.processed_preview_table.setColumnCount(len(base_df.columns))
        self.processed_preview_table.setHorizontalHeaderLabels([str(col) for col in base_df.columns])

        for row_index, (_, row) in enumerate(base_df.iterrows()):
            for col_index, value in enumerate(row):
                if pd.isna(value):
                    text = ""
                elif isinstance(value, (int, float, np.integer, np.floating)):
                    text = f"{float(value):.4g}"
                else:
                    text = str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.processed_preview_table.setItem(row_index, col_index, item)

        self.processed_preview_table.resizeColumnsToContents()
        self.engineered_preview_table.clear()
        self.engineered_preview_table.setRowCount(len(engineered_df))
        self.engineered_preview_table.setColumnCount(len(engineered_df.columns))
        self.engineered_preview_table.setHorizontalHeaderLabels([str(col) for col in engineered_df.columns])

        for row_index, (_, row) in enumerate(engineered_df.iterrows()):
            for col_index, value in enumerate(row):
                if pd.isna(value):
                    text = ""
                elif isinstance(value, (int, float, np.integer, np.floating)):
                    text = f"{float(value):.4g}"
                else:
                    text = str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.engineered_preview_table.setItem(row_index, col_index, item)

        self.engineered_preview_table.resizeColumnsToContents()
        self.processed_preview_info_label.setText(
            f"전처리 완료 데이터 전체 결과: 총 {len(df)}행 표시"
        )

    def render_training_placeholder(self):
        colors = self._theme()
        self.canvas.axes.clear()
        self.canvas.axes.axis("off")
        self.canvas.axes.set_facecolor(colors["panel_bg"])
        self.canvas.fig.patch.set_facecolor(colors["panel_bg"])
        self.canvas.axes.text(0.5, 0.58, "2번 탭에서 모델 학습 결과가 여기에 표시됩니다.", ha="center", va="center", fontsize=14, color=colors["text_sec"], transform=self.canvas.axes.transAxes)
        self.canvas.axes.text(0.5, 0.42, "먼저 1번 탭에서 전처리를 실행해 주세요.", ha="center", va="center", fontsize=11, color=colors["text_label"], transform=self.canvas.axes.transAxes)
        self.canvas.draw()

    def render_performance_placeholder(self):
        colors = self._theme()
        self.perf_canvas.figure.clear()
        ax = self.perf_canvas.figure.add_subplot(111)
        ax.axis("off")
        ax.set_facecolor(colors["panel_bg"])
        self.perf_canvas.figure.patch.set_facecolor(colors["panel_bg"])
        ax.text(0.5, 0.56, "모델 학습이 끝나면 상세 성능 분석 그래프가 여기에 표시됩니다.", ha="center", va="center", fontsize=14, color=colors["text_sec"], transform=ax.transAxes)
        ax.text(0.5, 0.40, "실제값과 예측값이 얼마나 비슷한지 특성별로 확인할 수 있습니다.", ha="center", va="center", fontsize=11, color=colors["text_label"], transform=ax.transAxes)
        self.perf_canvas.figure.tight_layout(pad=0.4)
        self.perf_canvas.draw()

    def reset_preprocessing_state(self, keep_file=True):
        current_file = self.data_engine.file_path if keep_file else None
        self.preprocessing_ready = False
        self.data_engine.df = None
        self.data_engine.last_quality_report = {}
        self.data_engine.set_selected_training_columns([])
        if not keep_file:
            self.data_engine.set_file_path(None)

        self.train_btn.setEnabled(False)
        self.go_to_training_btn.setEnabled(False)
        if hasattr(self, "go_to_model_training_btn"):
            self.go_to_model_training_btn.setEnabled(False)
        if hasattr(self, "generate_features_btn"):
            self.generate_features_btn.setEnabled(False)
        self.metrics_label.setText("<b>모델 성능 요약:</b><br>- 예측 정확도: N/A<br>- 평균 오차: N/A")
        self.training_data_status_label.setText("")
        self.training_status_label.setText("")
        self.quality_summary_label.setText("전처리 결과 요약이 아직 없습니다.")
        self.domain_rule_label.setText("도메인 검증은 '오스테나이트 조성 기준'과 '고온 특성 기준' 두 부류로 나누어 범위를 확인합니다.")
        self.processed_preview_info_label.setText("전처리를 실행하면 처리 완료된 전체 데이터를 아래 표에서 확인할 수 있습니다.")
        self.processed_preview_table.clear()
        self.processed_preview_table.setRowCount(0)
        self.processed_preview_table.setColumnCount(0)
        self.engineered_preview_table.clear()
        self.engineered_preview_table.setRowCount(0)
        self.engineered_preview_table.setColumnCount(0)
        if hasattr(self, "feature_selection_table"):
            self.feature_selection_table.clearContents()
            self.feature_selection_table.setRowCount(0)
            self.select_all_features_btn.setEnabled(False)
            self.clear_features_btn.setEnabled(False)
            self.feature_selection_status_label.setText(
                "▲ 먼저 전처리를 실행한 뒤, 이 탭에서 학습 컬럼을 선택해 주세요."
            )
        self.render_training_placeholder()
        self.render_performance_placeholder()

        if keep_file and current_file:
            self.file_path_label.setText(f"파일: {os.path.basename(current_file)}")
            self.status_label.setText("상태: 전처리 설정을 초기화했습니다. 다시 전처리를 실행해 주세요.")
        else:
            self.file_path_label.setText("파일: 선택되지 않음")
            self.status_label.setText("상태: 학습용 데이터를 선택해 주세요.")

    def on_reset_preprocessing_clicked(self):
        self.missing_combo.setCurrentIndex(0)
        self.outlier_combo.setCurrentIndex(0)
        self.invalid_type_combo.setCurrentIndex(0)
        self.iqr_spin.setValue(1.5)
        self.feature_engineering_check.blockSignals(True)
        self.feature_engineering_check.setChecked(False)
        self.feature_engineering_check.blockSignals(False)
        if hasattr(self, "training_input_combo"):
            self.training_input_combo.setCurrentIndex(0)
        self.reset_preprocessing_state(keep_file=True)

    def on_select_file_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "데이터 파일 열기",
            "",
            "데이터 파일 (*.xls *.xlsx *.xlsm *.csv)",
        )
        if not file_path:
            return

        self.data_engine.set_file_path(file_path)
        self.data_engine.df = None
        self.data_engine.last_quality_report = {}
        self.file_path_label.setText(f"파일: {os.path.basename(file_path)}")
        self.status_label.setText("상태: 새 데이터 파일이 선택되었습니다. 1번 탭에서 전처리를 실행해 주세요.")
        self.quality_summary_label.setText("전처리 결과 요약이 아직 없습니다.")
        self.domain_rule_label.setText("조성, 열처리 온도, 시간, 이진값 등에 대해 '말이 되는 범위'를 확인합니다.")
        self.processed_preview_info_label.setText("전처리를 실행하면 처리 완료된 전체 데이터를 아래 표에서 확인할 수 있습니다.")
        self.processed_preview_table.clear()
        self.processed_preview_table.setRowCount(0)
        self.processed_preview_table.setColumnCount(0)
        self.metrics_label.setText("<b>모델 성능 요약:</b><br>- 예측 정확도: N/A<br>- 평균 오차: N/A")
        self.reset_preprocessing_state(keep_file=True)
        self.status_label.setText("상태: 새 데이터 파일이 선택되었습니다. 전처리를 실행해 주세요.")
        self._update_project_tree()

    def on_preprocess_clicked(self):
        if not self.data_engine.file_path or not os.path.exists(self.data_engine.file_path):
            self.status_label.setText("상태: 오류 - 먼저 데이터 파일을 선택해 주세요.")
            return

        self.apply_quality_settings_from_ui()
        self.data_engine.quality_options["feature_engineering"] = False
        self.feature_engineering_check.blockSignals(True)
        self.feature_engineering_check.setChecked(False)
        self.feature_engineering_check.blockSignals(False)
        self.status_label.setText("상태: 1차 데이터 정제 전처리를 실행 중입니다.")
        self.preprocess_btn.setEnabled(False)
        self.processed_preview_info_label.setText("새 설정으로 전처리 중입니다. 완료되면 표가 갱신됩니다.")
        self.processed_preview_table.clear()
        self.processed_preview_table.setRowCount(0)
        self.processed_preview_table.setColumnCount(0)
        self.engineered_preview_table.clear()
        self.engineered_preview_table.setRowCount(0)
        self.engineered_preview_table.setColumnCount(0)

        try:
            processed_df = self.data_engine.load_data(include_engineered=False)
            self.update_quality_summary_from_report(self.data_engine.last_quality_report)
            self.populate_processed_preview(processed_df)
            self.populate_feature_selection_table(reset_selection=True)
            self.preprocessing_ready = True
            self.status_label.setText("상태: 1차 데이터 정제 전처리가 완료되었습니다.")
            self.training_data_status_label.setText(f"✓ 전처리 완료 — {len(processed_df)}행 준비됨. 모델 학습을 시작할 수 있습니다.")
            self.training_status_label.setText("상태: 전처리 완료. 2번 탭에서 모델을 학습할 수 있습니다.")
            self.generate_features_btn.setEnabled(True)
            self.train_btn.setEnabled(True)
            self.go_to_training_btn.setEnabled(True)
            self.refresh_feature_selection_summary()
            self._update_project_tree()
            self._sb_status.setText("● 전처리 완료")
            self._sb_status.setStyleSheet("color: #1E293B; font-size: 11px; font-weight: 700; padding: 0 10px;")
        except Exception as exc:
            self.preprocessing_ready = False
            self.train_btn.setEnabled(False)
            self.go_to_training_btn.setEnabled(False)
            self.generate_features_btn.setEnabled(False)
            self.status_label.setText(f"상태: 전처리 오류 - {exc}")
        finally:
            self.preprocess_btn.setEnabled(True)

    def on_generate_features_clicked(self):
        try:
            if self.data_engine.df is None or self.data_engine.df.empty:
                self.status_label.setText("상태: 먼저 데이터 전처리를 실행해 주세요.")
                return

            self.status_label.setText("상태: 2차 합금 지표 생성 전처리를 실행 중입니다.")
            self.generate_features_btn.setEnabled(False)
            self.data_engine.generate_engineered_features_on_current_df()
            self.feature_engineering_check.blockSignals(True)
            self.feature_engineering_check.setChecked(True)
            self.feature_engineering_check.blockSignals(False)
            self.update_quality_summary_from_report(self.data_engine.last_quality_report)
            self.populate_processed_preview(self.data_engine.df)
            self.populate_feature_selection_table(reset_selection=False)
            self.status_label.setText("상태: 합금 지표 생성이 완료되었습니다.")
            self.training_status_label.setText("상태: 합금 지표 생성 완료. 이제 선택한 학습 컬럼으로 모델을 학습할 수 있습니다.")
        except Exception as exc:
            self.status_label.setText(f"상태: 합금 지표 생성 오류 - {exc}")
        finally:
            self.generate_features_btn.setEnabled(True)

    def show_austenite_domain_dialog(self):
        self.show_domain_range_dialog("오스테나이트 조성 기준")

    def show_high_temp_domain_dialog(self):
        self.show_domain_range_dialog("고온 특성 기준")

    def show_domain_range_dialog(self, group_filter=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("도메인 기준 설정")
        dialog.resize(760, 620)

        layout = QVBoxLayout(dialog)
        intro = QLabel("각 컬럼의 최소값과 최대값을 직접 설정할 수 있습니다. SSINA 기준을 반영해 오스테나이트 조성 기준과 고온 특성 기준 두 부류로 나누어 표시합니다.")
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 13px; color: #334155; font-weight: 600; padding-bottom: 4px;")
        layout.addWidget(intro)

        table = QTableWidget(dialog)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["부류", "컬럼", "최소값", "최대값", "근거"])
        domain_ranges = self.data_engine.get_domain_ranges()
        sorted_columns = sorted(
            [
                col
                for col in domain_ranges.keys()
                if group_filter is None or self.data_engine.get_domain_group(col) == group_filter
            ],
            key=lambda col: (self.data_engine.get_domain_group(col), col),
        )
        table.setRowCount(len(sorted_columns))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        for row, column in enumerate(sorted_columns):
            lower_bound, upper_bound = domain_ranges[column]
            group = self.data_engine.get_domain_group(column)
            basis = self.data_engine.get_domain_basis(column)
            source = "사용자 지정" if column in self.data_engine.custom_ranges else basis
            group_item = QTableWidgetItem(group)
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, group_item)
            name_item = QTableWidgetItem(column)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, name_item)
            table.setItem(row, 2, QTableWidgetItem("" if lower_bound is None else str(lower_bound)))
            table.setItem(row, 3, QTableWidgetItem("" if upper_bound is None else str(upper_bound)))
            source_item = QTableWidgetItem(source)
            source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 4, source_item)

        layout.addWidget(table, 1)

        button_row = QHBoxLayout()
        reset_btn = QPushButton("기본값으로 되돌리기")
        apply_btn = QPushButton("적용")
        close_btn = QPushButton("닫기")
        button_row.addWidget(reset_btn)
        button_row.addStretch()
        button_row.addWidget(apply_btn)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        def apply_ranges(reset_to_default=False):
            if reset_to_default:
                self.data_engine.reset_custom_domain_ranges()
                self.refresh_domain_range_status()
                self.domain_rule_label.setText("도메인 검증은 '오스테나이트 조성 기준'과 '고온 특성 기준' 두 부류로 나누어 범위를 확인합니다.")
                self.mark_preprocessing_dirty()
                dialog.accept()
                return

            custom_ranges = {}
            for row, column in enumerate(sorted_columns):
                min_item = table.item(row, 2)
                max_item = table.item(row, 3)
                min_text = min_item.text().strip() if min_item and min_item.text() else ""
                max_text = max_item.text().strip() if max_item and max_item.text() else ""

                try:
                    lower_bound = None if min_text == "" else float(min_text)
                    upper_bound = None if max_text == "" else float(max_text)
                except ValueError:
                    QMessageBox.warning(dialog, "입력 오류", f"{column} 값의 최소값 또는 최대값이 숫자가 아닙니다.")
                    return

                if lower_bound is not None and upper_bound is not None and lower_bound > upper_bound:
                    QMessageBox.warning(dialog, "입력 오류", f"{column} 값에서 최소값이 최대값보다 큽니다.")
                    return

                default_bounds = self.data_engine.default_domain_ranges.get(column)
                current_bounds = (lower_bound, upper_bound)
                if default_bounds is None or current_bounds != default_bounds:
                    custom_ranges[column] = current_bounds

            self.data_engine.set_custom_domain_ranges(custom_ranges)
            self.refresh_domain_range_status()
            self.domain_rule_label.setText("도메인 검증은 '오스테나이트 조성 기준'과 '고온 특성 기준' 두 부류의 범위를 기준으로 비정상 값을 확인합니다.")
            self.mark_preprocessing_dirty()
            QMessageBox.information(dialog, "적용 완료", "도메인 기준이 저장되었습니다. 전처리를 다시 실행하면 반영됩니다.")
            dialog.accept()

        reset_btn.clicked.connect(lambda: apply_ranges(True))
        apply_btn.clicked.connect(apply_ranges)
        close_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def _on_preview_table_context_menu(self, table, pos):
        item = table.itemAt(pos)
        if item is None:
            return
        from PyQt6.QtWidgets import QApplication, QMenu
        col = item.column()
        header = table.horizontalHeaderItem(col)
        col_name = header.text() if header else ""
        menu = QMenu(self)
        copy_cell = menu.addAction(f"셀 복사  ({item.text()})")
        copy_row = menu.addAction("행 전체 복사")
        action = menu.exec(table.viewport().mapToGlobal(pos))
        if action == copy_cell:
            QApplication.clipboard().setText(item.text())
            self.status_label.setText(f"상태: [{col_name}] {item.text()} 복사됨")
        elif action == copy_row:
            row = item.row()
            cells = []
            for c in range(table.columnCount()):
                cell = table.item(row, c)
                cells.append(cell.text() if cell else "")
            QApplication.clipboard().setText("\t".join(cells))
            self.status_label.setText(f"상태: {row + 1}행 복사됨 ({table.columnCount()}개 값)")

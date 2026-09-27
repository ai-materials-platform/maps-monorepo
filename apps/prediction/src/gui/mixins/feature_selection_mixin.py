from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem


class FeatureSelectionMixin:
    def populate_feature_selection_table(self, reset_selection=False):
        available_columns = self.data_engine.get_available_training_columns(include_engineered=True)
        previous_selection = [] if reset_selection else self.data_engine.get_selected_training_columns(default_to_all=False)
        if reset_selection or self.data_engine.selected_training_columns is None:
            selected_columns = list(available_columns)
        else:
            selected_columns = [col for col in available_columns if col in previous_selection]

        self.data_engine.set_selected_training_columns(selected_columns)

        self.feature_selection_table.blockSignals(True)
        self.feature_selection_table.clearContents()
        self.feature_selection_table.setRowCount(len(available_columns))

        for row, column in enumerate(available_columns):
            use_item = QTableWidgetItem()
            use_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            use_item.setCheckState(
                Qt.CheckState.Checked if column in selected_columns else Qt.CheckState.Unchecked
            )
            self.feature_selection_table.setItem(row, 0, use_item)

            name_item = QTableWidgetItem(column)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.feature_selection_table.setItem(row, 1, name_item)

            column_type = "합금 지표" if column in self.data_engine.engineered_feature_cols else "원본"
            type_item = QTableWidgetItem(column_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.feature_selection_table.setItem(row, 2, type_item)

        self.feature_selection_table.blockSignals(False)
        self.feature_selection_table.resizeColumnsToContents()

        has_columns = bool(available_columns)
        self.select_all_features_btn.setEnabled(has_columns)
        self.clear_features_btn.setEnabled(has_columns)
        self.refresh_feature_selection_summary()

    def get_checked_feature_columns_from_table(self):
        selected_columns = []
        for row in range(self.feature_selection_table.rowCount()):
            use_item = self.feature_selection_table.item(row, 0)
            name_item = self.feature_selection_table.item(row, 1)
            if use_item and name_item and use_item.checkState() == Qt.CheckState.Checked:
                selected_columns.append(name_item.text())
        return selected_columns

    def refresh_feature_selection_summary(self):
        available_columns = self.data_engine.get_available_training_columns(include_engineered=True)
        selected_columns = self.data_engine.get_selected_training_columns(default_to_all=False)

        if not available_columns:
            self.feature_selection_status_label.setText(
                "▲ 먼저 전처리를 실행한 뒤, 이 탭에서 학습 컬럼을 선택해 주세요."
            )
            self.go_to_model_training_btn.setEnabled(False)
            return

        raw_count = sum(1 for col in selected_columns if col in self.data_engine.raw_feature_cols)
        engineered_count = sum(
            1 for col in selected_columns if col in self.data_engine.engineered_feature_cols
        )
        self.feature_selection_status_label.setText(
            f"✓ 전체 {len(available_columns)}개 중 {len(selected_columns)}개 컬럼이 선택되었습니다. "
            f"(원본 {raw_count}개, 합금 지표 {engineered_count}개)"
        )
        self.go_to_model_training_btn.setEnabled(self.preprocessing_ready and bool(selected_columns))

        if self.preprocessing_ready:
            if selected_columns:
                self.train_btn.setEnabled(True)
                self.training_data_status_label.setText(
                    f"✓ 전처리 완료 — 선택한 {len(selected_columns)}개 컬럼으로 학습합니다."
                )
            else:
                self.train_btn.setEnabled(False)
                self.training_data_status_label.setText(
                    "▲ 전처리는 완료되었지만 아직 학습 컬럼이 선택되지 않았습니다."
                )

    def on_feature_selection_item_changed(self, item):
        if item.column() != 0:
            return
        self.data_engine.set_selected_training_columns(self.get_checked_feature_columns_from_table())
        self.refresh_feature_selection_summary()

    def select_all_feature_columns(self):
        self.feature_selection_table.blockSignals(True)
        for row in range(self.feature_selection_table.rowCount()):
            item = self.feature_selection_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        self.feature_selection_table.blockSignals(False)
        self.data_engine.set_selected_training_columns(self.get_checked_feature_columns_from_table())
        self.refresh_feature_selection_summary()

    def clear_all_feature_columns(self):
        self.feature_selection_table.blockSignals(True)
        for row in range(self.feature_selection_table.rowCount()):
            item = self.feature_selection_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.feature_selection_table.blockSignals(False)
        self.data_engine.set_selected_training_columns(self.get_checked_feature_columns_from_table())
        self.refresh_feature_selection_summary()

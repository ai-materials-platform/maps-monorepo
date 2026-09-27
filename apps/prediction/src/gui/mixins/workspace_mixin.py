import csv
import datetime
import json
import os
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class WorkspaceMixin:
    def _ws_root(self):
        """워크스페이스 베이스 디렉토리.
        AI_MAPS_WORKSPACE_ROOT 환경변수가 있으면 그 경로를 사용 (패키징 배포 시 AppData)."""
        return os.environ.get('AI_MAPS_WORKSPACE_ROOT', 'workspaces')

    def _ws_project_dir(self):
        """현재 활성 프로젝트의 워크스페이스 저장 루트.
        프로젝트가 없으면 ws_root/ 공용 디렉토리를 사용한다."""
        active = getattr(self, '_active_workspace_name', None) or ''
        if active:
            return os.path.join(self._ws_root(), active)
        return self._ws_root()

    def auto_save_workspace(self):
        # auto_save는 항상 공유 임시 폴더 — 프로젝트 워크스페이스엔 명시 저장만 기록됨
        folder = os.path.join(self._ws_root(), "auto_save")
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
        state = {
            "file_path": self.data_engine.file_path,
            "model_combo_index": self.model_combo.currentIndex(),
            "max_iter": self.iter_spin.value(),
            "inputs": {k: v.text() for k, v in self.inputs.items()},
            "preprocessing": {
                "missing_combo": self.missing_combo.currentIndex(),
                "outlier_combo": self.outlier_combo.currentIndex(),
                "invalid_type_combo": self.invalid_type_combo.currentIndex(),
                "iqr_spin": self.iqr_spin.value(),
                "training_input_combo": 0,
                "preprocessing_ready": self.preprocessing_ready,
            },
        }
        with open(os.path.join(folder, "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        self.canvas.fig.savefig(os.path.join(folder, "training.png"), dpi=200, bbox_inches="tight")
        self.perf_canvas.figure.savefig(os.path.join(folder, "performance.png"), dpi=200, bbox_inches="tight")
        self.stress_strain_canvas.fig.savefig(os.path.join(folder, "stress_strain_curve.png"), dpi=200, bbox_inches="tight")
        pre_df = self.data_engine.get_preprocessed_display_df()
        if not pre_df.empty:
            pre_df.to_csv(os.path.join(folder, "preprocessed_data.csv"), index=False, encoding="utf-8-sig")
        eng_df = self.data_engine.get_engineered_display_df()
        if not eng_df.empty:
            eng_df.to_csv(os.path.join(folder, "engineered_data.csv"), index=False, encoding="utf-8-sig")

    def append_log(self, entry):
        ws_dir = self._ws_root()
        if not os.path.exists(ws_dir):
            os.makedirs(ws_dir)
        log_path = os.path.join(ws_dir, "log.json")
        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        entry["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logs.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def delete_workspace(self):
        name = self.ws_combo.currentText()
        if not name:
            self.status_label.setText("상태: 삭제할 분석 기록를 선택해 주세요")
            return
        reply = QMessageBox.question(self, "삭제 확인",
            f"'{name}' 분석 기록를 삭제하시겠습니까?\n(폴더 전체가 삭제됩니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
        folder = os.path.join(self._ws_project_dir(), name)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        self.refresh_workspace_list()
        self.status_label.setText(f"상태: 분석 기록 '{name}' 삭제 완료")

    def refresh_workspace_list(self):
        ws_dir = self._ws_project_dir()
        self.ws_combo.clear()
        if os.path.exists(ws_dir):
            names = sorted([d for d in os.listdir(ws_dir)
                            if os.path.isdir(os.path.join(ws_dir, d)) and d != "auto_save"])
            self.ws_combo.addItems(names)
        if hasattr(self, "ws_table"):
            self.refresh_workspace_table()

    def refresh_workspace_table(self):
        ws_dir = self._ws_project_dir()
        search_text = getattr(self, "_ws_search_text", "").lower().strip()

        all_names = []
        if os.path.exists(ws_dir):
            all_names = sorted([d for d in os.listdir(ws_dir)
                                if os.path.isdir(os.path.join(ws_dir, d)) and d != "auto_save"])

        filtered = [n for n in all_names if search_text in n.lower()] if search_text else list(all_names)
        total = len(filtered)

        page = getattr(self, "_ws_page", 0)
        per_page = getattr(self, "_ws_rows_per_page", 10)
        max_page = max(0, (total - 1) // per_page) if total > 0 else 0
        page = min(page, max_page)
        self._ws_page = page

        start = page * per_page
        end = min(start + per_page, total)
        page_names = filtered[start:end]

        self.ws_table.setRowCount(0)
        model_name_map = {"RF": "Random Forest", "GBM": "Gradient Boosting", "MLP": "Neural Network", "TFP": "TFP"}

        for row, name in enumerate(page_names):
            self.ws_table.insertRow(row)
            folder = os.path.join(ws_dir, name)  # ws_dir already points to project dir
            state_path = os.path.join(folder, "state.json")
            state = {}
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)

            self.ws_table.setItem(row, 0, QTableWidgetItem(name))

            model_idx = state.get("model_combo_index", -1)
            model_keys = ["RF", "GBM", "MLP", "TFP"]
            model_key = model_keys[model_idx] if 0 <= model_idx < len(model_keys) else "-"
            self.ws_table.setItem(row, 1, QTableWidgetItem(model_name_map.get(model_key, "-")))

            self.ws_table.setItem(row, 2, QTableWidgetItem(state.get("saved_date", "-")))

            ss_log_path = os.path.join(folder, "stress_strain_log.json")
            초기값_text = 회복_text = 복원_text = 끊김_text = "-"
            if os.path.exists(ss_log_path):
                try:
                    with open(ss_log_path, "r", encoding="utf-8") as f:
                        ss = json.load(f)
                    초기 = ss.get("초기값", {})
                    yield_s = 초기.get("yield_stress_MPa", "-")
                    uts_s = 초기.get("UTS_MPa", "-")
                    초기값_text = f"{yield_s} MPa"
                    회복_text = f"0 ~ {yield_s} MPa"
                    복원_text = f"{yield_s} ~ {uts_s} MPa"
                    frac_s = ss.get("끊기는_구간", {}).get("Fracture_point", {}).get("stress_MPa", "-")
                    끊김_text = f"{uts_s} → {frac_s} MPa"
                except Exception:
                    pass
            self.ws_table.setItem(row, 3, QTableWidgetItem(초기값_text))
            self.ws_table.setItem(row, 4, QTableWidgetItem(회복_text))
            self.ws_table.setItem(row, 5, QTableWidgetItem(복원_text))
            self.ws_table.setItem(row, 6, QTableWidgetItem(끊김_text))
            self._ws_add_action_btn(row, name, folder)

        if hasattr(self, "ws_count_badge"):
            self.ws_count_badge.setText(f"({total})")
        if hasattr(self, "ws_page_info_label"):
            self.ws_page_info_label.setText(f"{start + 1}–{end} / {total}" if total > 0 else "0 / 0")
        if hasattr(self, "ws_prev_page_btn"):
            self.ws_prev_page_btn.setEnabled(page > 0)
        if hasattr(self, "ws_next_page_btn"):
            self.ws_next_page_btn.setEnabled(end < total)

    def _ws_add_action_btn(self, row, name, folder):
        btn = QPushButton("···")
        btn.setFixedSize(36, 28)
        btn.setStyleSheet(
            "QPushButton { background: transparent; color: #6B7280; border: none; "
            "border-radius: 4px; font-size: 14px; font-weight: 900; letter-spacing: 2px; }"
            "QPushButton:hover { background: #F3F4F6; color: #111827; }"
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        _name, _folder = name, folder

        def show_menu():
            menu = QMenu(self)
            load_action = menu.addAction("불러오기")
            menu.addSeparator()
            pred_path = os.path.join(_folder, "prediction_result.csv")
            curve_path = os.path.join(_folder, "stress_strain_curve.csv")
            pred_action = menu.addAction("예측 CSV 열기")
            pred_action.setEnabled(os.path.exists(pred_path))
            curve_action = menu.addAction("커브 CSV 열기")
            curve_action.setEnabled(os.path.exists(curve_path))
            menu.addSeparator()
            delete_action = menu.addAction("삭제")
            action = menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
            if action == load_action:
                self._load_workspace_by_name(_name)
            elif action == pred_action and os.path.exists(pred_path):
                os.startfile(pred_path)
            elif action == curve_action and os.path.exists(curve_path):
                os.startfile(curve_path)
            elif action == delete_action:
                self._delete_workspace_by_name(_name)

        btn.clicked.connect(show_menu)
        cell_w = QWidget()
        cell_l = QHBoxLayout(cell_w)
        cell_l.setContentsMargins(4, 2, 4, 2)
        cell_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cell_l.addWidget(btn)
        self.ws_table.setCellWidget(row, 7, cell_w)

    def _ws_on_search_changed(self, text):
        self._ws_search_text = text
        self._ws_page = 0
        self.refresh_workspace_table()

    def _ws_prev_page(self):
        if getattr(self, "_ws_page", 0) > 0:
            self._ws_page -= 1
            self.refresh_workspace_table()

    def _ws_next_page(self):
        self._ws_page = getattr(self, "_ws_page", 0) + 1
        self.refresh_workspace_table()

    def _load_workspace_by_name(self, name):
        reply = QMessageBox.question(
            self, "불러오기 확인",
            f"'{name}' 분석을 불러오시겠습니까?\n현재 작업 중인 내용이 변경될 수 있습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.ws_combo.setCurrentText(name)
        self.load_workspace()
        self.tabs.setCurrentIndex(0)

    def _on_ws_table_clicked(self, *_):
        pass

    def _on_ws_table_context_menu(self, pos):
        row = self.ws_table.rowAt(pos.y())
        if row < 0:
            return
        name_item = self.ws_table.item(row, 0)
        if not name_item:
            return
        folder = os.path.join(self._ws_project_dir(), name_item.text())
        menu = QMenu(self)
        load_action = menu.addAction("불러오기")
        menu.addSeparator()
        pred_path = os.path.join(folder, "prediction_result.csv")
        curve_path = os.path.join(folder, "stress_strain_curve.csv")
        pred_action = menu.addAction("예측 CSV 열기")
        pred_action.setEnabled(os.path.exists(pred_path))
        curve_action = menu.addAction("커브 CSV 열기")
        curve_action.setEnabled(os.path.exists(curve_path))
        menu.addSeparator()
        delete_action = menu.addAction("삭제")
        action = menu.exec(self.ws_table.viewport().mapToGlobal(pos))
        name = name_item.text()
        if action == load_action:
            self._load_workspace_by_name(name)
        elif action == pred_action and os.path.exists(pred_path):
            os.startfile(pred_path)
        elif action == curve_action and os.path.exists(curve_path):
            os.startfile(curve_path)
        elif action == delete_action:
            self._delete_workspace_by_name(name)

    def _delete_workspace_by_name(self, name):
        reply = QMessageBox.question(
            self, "삭제 확인",
            f"'{name}' 분석 기록을 삭제하시겠습니까?\n(폴더 전체가 삭제됩니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        folder = os.path.join(self._ws_project_dir(), name)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        self.refresh_workspace_list()
        self.status_label.setText(f"상태: 분석 기록 '{name}' 삭제 완료")

    def _show_full_graph_dialog(self, path):
        if not path or not os.path.exists(path):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("그래프 크게 보기")
        dialog.resize(1100, 860)
        layout = QVBoxLayout(dialog)

        orig_pix = QPixmap(path)
        init_zoom = min(1040 / orig_pix.width(), 780 / orig_pix.height(), 1.0) if orig_pix.width() > 0 else 1.0
        zoom = [init_zoom]

        scroll = QScrollArea()
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(img_label)
        layout.addWidget(scroll)

        def render():
            w = int(orig_pix.width() * zoom[0])
            h = int(orig_pix.height() * zoom[0])
            scaled = orig_pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(scaled)
            img_label.resize(scaled.width(), scaled.height())

        render()

        def zoom_in():
            zoom[0] = min(zoom[0] * 1.25, 8.0); render()
        def zoom_out():
            zoom[0] = max(zoom[0] * 0.8, init_zoom); render()
        def zoom_reset():
            zoom[0] = 1.0; render()

        scroll.wheelEvent = lambda e: zoom_in() if e.angleDelta().y() > 0 else zoom_out()

        btn_row = QHBoxLayout()
        for label, fn, color in [("확대 (+)", zoom_in, "#2980b9"), ("원래 크기", zoom_reset, "#27ae60")]:
            b = QPushButton(label)
            b.setFixedWidth(90)
            b.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 5px;")
            b.clicked.connect(fn)
            btn_row.addWidget(b)
        btn_row.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.setFixedWidth(90)
        close_btn.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 5px;")
        close_btn.clicked.connect(dialog.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.destroyed.connect(lambda: self._open_dialogs.remove(dialog) if dialog in self._open_dialogs else None)
        self._open_dialogs.append(dialog)
        dialog.show()

    def _on_thumb_clicked(self, _):
        self._show_full_graph_dialog(self._ws_thumb_full_path)

    def _on_perf_thumb_clicked(self, _):
        self._show_full_graph_dialog(self._ws_perf_thumb_full_path)

    def _show_image_on_canvas(self, canvas, image):
        canvas.fig.clear()
        ax = canvas.fig.add_subplot(111)
        canvas.axes = ax
        canvas._view_mode = "image"
        ax.imshow(image)
        ax.axis("off")
        canvas.fig.tight_layout(pad=0.4)
        canvas.draw()

    def _on_compare_clicked(self):
        selected_rows = list({idx.row() for idx in self.ws_table.selectedIndexes()})
        if len(selected_rows) < 2:
            QMessageBox.information(self, "비교", "비교할 분석을 2개 이상 선택해 주세요.\n(Ctrl+클릭으로 여러 행 선택)")
            return
        if len(selected_rows) > 3:
            QMessageBox.warning(self, "비교", "최대 3개까지만 비교할 수 있습니다.")
            return

        names = [self.ws_table.item(r, 0).text() for r in selected_rows if self.ws_table.item(r, 0)]
        n = len(names)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"분석 비교 — {' vs '.join(names)}")
        dialog.resize(500 * n, 900)
        outer = QVBoxLayout(dialog)

        all_pairs = []
        init_zoom_cmp = 0.5
        zoom = [init_zoom_cmp]

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        scroll_area.setWidget(content_widget)
        outer.addWidget(scroll_area)

        for graph_file, graph_label in [("training.png", "학습 그래프"), ("performance.png", "상세 성능")]:
            section_lbl = QLabel(f"▶ {graph_label}")
            section_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #2c3e50; margin-top: 8px;")
            content_layout.addWidget(section_lbl)

            row_layout = QHBoxLayout()
            for name in names:
                col = QVBoxLayout()
                name_lbl = QLabel(name)
                name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                name_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #8e44ad;")
                col.addWidget(name_lbl)

                img_lbl = QLabel()
                img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_lbl.setStyleSheet("border: 1px solid #dde1e6; background: white;")
                path = os.path.join(self._ws_project_dir(), name, graph_file)
                if os.path.exists(path):
                    orig_pix = QPixmap(path)
                    all_pairs.append((orig_pix, img_lbl))
                else:
                    img_lbl.setText("그래프 없음")
                    img_lbl.setFixedSize(380, 260)
                col.addWidget(img_lbl)
                row_layout.addLayout(col)
            content_layout.addLayout(row_layout)

        def render_all():
            for orig_pix, img_lbl in all_pairs:
                w = int(orig_pix.width() * zoom[0])
                h = int(orig_pix.height() * zoom[0])
                scaled = orig_pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_lbl.setPixmap(scaled)
                img_lbl.resize(scaled.width(), scaled.height())

        render_all()

        def zoom_in():
            zoom[0] = min(zoom[0] * 1.25, 8.0); render_all()
        def zoom_out():
            zoom[0] = max(zoom[0] * 0.8, init_zoom_cmp); render_all()
        def zoom_reset():
            zoom[0] = 0.5; render_all()

        scroll_area.wheelEvent = lambda e: zoom_in() if e.angleDelta().y() > 0 else zoom_out()

        btn_row = QHBoxLayout()
        for label, fn, color in [("확대 (+)", zoom_in, "#2980b9"), ("원래 크기", zoom_reset, "#27ae60")]:
            b = QPushButton(label)
            b.setFixedWidth(90)
            b.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; padding: 5px;")
            b.clicked.connect(fn)
            btn_row.addWidget(b)
        btn_row.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.setFixedWidth(90)
        close_btn.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; padding: 5px;")
        close_btn.clicked.connect(dialog.close)
        btn_row.addWidget(close_btn)
        outer.addLayout(btn_row)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.destroyed.connect(lambda: self._open_dialogs.remove(dialog) if dialog in self._open_dialogs else None)
        self._open_dialogs.append(dialog)
        dialog.show()

    def _load_selected_ws(self):
        selected = self.ws_table.selectedItems()
        if not selected:
            return
        row = self.ws_table.currentRow()
        self._on_ws_table_double_clicked(row, 0)

    def _on_ws_table_double_clicked(self, row, col):
        if col == 7:
            return
        name_item = self.ws_table.item(row, 0)
        if not name_item:
            return
        self._load_workspace_by_name(name_item.text())

    def _open_workspace_dialog(self):
        if not hasattr(self, "_ws_dialog") or not self._ws_dialog:
            dlg = QDialog(self)
            dlg.setWindowTitle("분석 기록")
            dlg.resize(1100, 660)
            dlg.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowCloseButtonHint |
                Qt.WindowType.WindowMinMaxButtonsHint
            )
            dlg_layout = QVBoxLayout(dlg)
            dlg_layout.setContentsMargins(0, 0, 0, 0)
            self._workspace_widget.setParent(dlg)
            dlg_layout.addWidget(self._workspace_widget)
            self._ws_dialog = dlg
        self._workspace_widget.show()
        self._ws_dialog.show()
        self._ws_dialog.raise_()
        self._ws_dialog.activateWindow()
        self.refresh_workspace_table()

    def _save_workspace_from_menu(self):
        name, ok = QInputDialog.getText(
            self, "분석 기록 저장", "저장할 이름을 입력하세요:",
            text=self.ws_name_input.text().strip()
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "이름 필요", "분석 기록 이름을 입력해 주세요.")
            return
        self.ws_name_input.setText(name)
        self.save_workspace()

    def save_workspace(self):
        name = self.ws_name_input.text().strip()
        if not name:
            self.status_label.setText("상태: 분석 기록 이름을 입력해 주세요")
            return
        folder = os.path.join(self._ws_project_dir(), name)
        if os.path.exists(folder):
            reply = QMessageBox.question(self, "덮어쓰기 확인",
                f"'{name}' 분석 기록가 이미 존재합니다.\n덮어쓰시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        else:
            os.makedirs(folder)
        self.canvas.fig.savefig(os.path.join(folder, "training.png"), dpi=200, bbox_inches="tight")
        self.perf_canvas.figure.savefig(os.path.join(folder, "performance.png"), dpi=200, bbox_inches="tight")
        self.prediction_canvas.fig.savefig(os.path.join(folder, "prediction.png"), dpi=200, bbox_inches="tight")
        self.stress_strain_canvas.fig.savefig(os.path.join(folder, "stress_strain_curve.png"), dpi=200, bbox_inches="tight")
        state = {
            "file_path": self.data_engine.file_path,
            "model_combo_index": self.model_combo.currentIndex(),
            "max_iter": self.iter_spin.value(),
            "inputs": {k: v.text() for k, v in self.inputs.items()},
            "saved_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "r2_avg": self.last_r2_avg,
            "preprocessing": {
                "missing_combo": self.missing_combo.currentIndex(),
                "outlier_combo": self.outlier_combo.currentIndex(),
                "invalid_type_combo": self.invalid_type_combo.currentIndex(),
                "iqr_spin": self.iqr_spin.value(),
                "training_input_combo": 0,
                "preprocessing_ready": self.preprocessing_ready,
            },
        }
        _user_ps = getattr(self, "_user_prediction_state", None)
        if _user_ps:
            state["prediction_mean"] = [float(x) for x in _user_ps["mean"]]
            state["prediction_std"] = [float(x) for x in _user_ps["std"]]
            state["prediction_inputs"] = dict(_user_ps["input_dict"])
        _pre_ps = getattr(self, "_pretrained_prediction_state", None)
        if _pre_ps:
            state["pretrained_prediction_mean"] = [float(x) for x in _pre_ps["mean"]]
            state["pretrained_prediction_std"] = [float(x) for x in _pre_ps["std"]]
            state["pretrained_prediction_inputs"] = dict(_pre_ps["input_dict"])
        with open(os.path.join(folder, "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        pre_df = self.data_engine.get_preprocessed_display_df()
        if not pre_df.empty:
            pre_df.to_csv(os.path.join(folder, "preprocessed_data.csv"), index=False, encoding="utf-8-sig")
        eng_df = self.data_engine.get_engineered_display_df()
        if not eng_df.empty:
            eng_df.to_csv(os.path.join(folder, "engineered_data.csv"), index=False, encoding="utf-8-sig")
        pred_state = getattr(self, "_user_prediction_state", None) or getattr(self, "_pretrained_prediction_state", None)
        if pred_state:
            try:
                mean = pred_state.get("mean")
                input_dict = pred_state.get("input_dict", {})
                _, _, points, meta, _ = self._build_stress_strain_profile(mean, input_dict)
                ss_log = {
                    "초기값": {
                        "yield_stress_MPa": round(meta["yield_stress"], 2),
                        "UTS_MPa": round(meta["uts"], 2),
                        "elongation_pct": round(meta["elongation_pct"], 2),
                        "area_reduction_pct": round(meta["area_reduction_pct"], 2),
                        "elastic_modulus_GPa": round(meta["elastic_modulus_gpa"], 1),
                    },
                    "회복_구간": {
                        "설명": "하중 제거 시 완전 복원 가능한 탄성 구간",
                        "strain_범위": [0.0, round(meta["yield_strain"], 5)],
                        "stress_범위_MPa": [0.0, round(meta["yield_stress"], 2)],
                        "Yield_point": {
                            "strain": round(points["Yield"][0], 5),
                            "stress_MPa": round(points["Yield"][1], 2),
                        },
                    },
                    "복원불가_구간": {
                        "설명": "소성 변형 → 영구 변형 구간 (Yield ~ UTS)",
                        "strain_범위": [round(meta["yield_strain"], 5), round(points["UTS"][0], 5)],
                        "UTS_point": {
                            "strain": round(points["UTS"][0], 5),
                            "stress_MPa": round(points["UTS"][1], 2),
                        },
                    },
                    "끊기는_구간": {
                        "설명": "네킹 시작 → 파단 완료 구간 (UTS 이후 응력 감소, 재료 분리)",
                        "strain_범위": [round(points["UTS"][0], 5), round(meta["fracture_strain"], 5)],
                        "Fracture_point": {
                            "strain": round(points["Fracture"][0], 5),
                            "stress_MPa": round(points["Fracture"][1], 2),
                        },
                    },
                }
                with open(os.path.join(folder, "stress_strain_log.json"), "w", encoding="utf-8") as f:
                    json.dump(ss_log, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("stress_strain_log 저장 실패:", e)

        pred_csv_state = getattr(self, "_user_prediction_state", None) or getattr(self, "_pretrained_prediction_state", None)
        if pred_csv_state:
            try:
                mean = pred_csv_state["mean"]
                std  = pred_csv_state["std"]
                inputs = pred_csv_state["input_dict"]
                targets = [
                    ("0.2% 항복강도 (MPa)", mean[0], std[0]),
                    ("인장강도 UTS (MPa)",   mean[1], std[1]),
                    ("연신율 (%)",           mean[2], std[2]),
                    ("단면감소율 (%)",        mean[3], std[3]),
                ]
                with open(os.path.join(folder, "prediction_result.csv"), "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["=== 입력 조성 / 공정 조건 ==="])
                    writer.writerow(["항목", "값"])
                    for k, v in inputs.items():
                        writer.writerow([k, v])
                    writer.writerow([])
                    writer.writerow(["=== 예측 결과 ==="])
                    writer.writerow(["항목", "예측값", "불확실도 (±)"])
                    for label, m, s in targets:
                        writer.writerow([label, f"{m:.2f}", f"{s:.2f}"])
            except Exception as e:
                print("prediction_result.csv 저장 실패:", e)
            try:
                strain_arr, stress_arr, points, meta, segments = self._build_stress_strain_profile(
                    pred_csv_state["mean"], pred_csv_state["input_dict"]
                )
                with open(os.path.join(folder, "stress_strain_curve.csv"), "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Strain", "Stress (MPa)", "구간"])
                    for s, st in zip(*segments["elastic"]):
                        writer.writerow([f"{s:.6f}", f"{st:.4f}", "탄성"])
                    hx, hy = segments["hardening"]
                    for s, st in zip(hx[1:], hy[1:]):
                        writer.writerow([f"{s:.6f}", f"{st:.4f}", "가공경화"])
                    nx, ny = segments["necking"]
                    for s, st in zip(nx[1:], ny[1:]):
                        writer.writerow([f"{s:.6f}", f"{st:.4f}", "네킹/파단"])
            except Exception as e:
                print("stress_strain_curve.csv 저장 실패:", e)

        self.refresh_workspace_list()
        self.status_label.setText(f"상태: 분석 기록 '{name}' 저장 완료")

    def load_workspace(self, name=None):
        if name is None:
            name = self.ws_combo.currentText()
        if not name:
            self.status_label.setText("상태: 불러올 분석 기록를 선택해 주세요")
            return
        folder = os.path.join(self._ws_project_dir(), name)
        state_path = os.path.join(folder, "state.json")
        if not os.path.exists(state_path):
            # 새 프로젝트 — 폴더만 만들어 두고 빈 상태로 시작
            os.makedirs(folder, exist_ok=True)
            self.status_label.setText(f"상태: 새 프로젝트 '{name}' — 데이터를 불러와 시작하세요")
            return
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self._user_prediction_state = None
        if hasattr(self, "user_simulation_widget"):
            self.user_simulation_widget.clear_profile()
        saved_file = state.get("file_path")
        if saved_file and os.path.exists(saved_file):
            self.data_engine.set_file_path(saved_file)
            self.file_path_label.setText(f"파일: {os.path.basename(saved_file)}")
        self.model_combo.setCurrentIndex(state.get("model_combo_index", 0))
        self.iter_spin.setValue(state.get("max_iter", 2000))
        for k, v in state.get("inputs", {}).items():
            if k in self.inputs:
                self.inputs[k].setText(v)

        pre = state.get("preprocessing", {})
        if pre:
            self.missing_combo.blockSignals(True)
            self.outlier_combo.blockSignals(True)
            self.invalid_type_combo.blockSignals(True)
            self.iqr_spin.blockSignals(True)
            self.missing_combo.setCurrentIndex(pre.get("missing_combo", 0))
            self.outlier_combo.setCurrentIndex(pre.get("outlier_combo", 0))
            self.invalid_type_combo.setCurrentIndex(pre.get("invalid_type_combo", 0))
            self.iqr_spin.setValue(pre.get("iqr_spin", 1.5))
            if hasattr(self, "training_input_combo"):
                self.training_input_combo.setCurrentIndex(0)
            self.preprocessing_ready = pre.get("preprocessing_ready", False)
            self.train_btn.setEnabled(self.preprocessing_ready)
            self.go_to_training_btn.setEnabled(self.preprocessing_ready)
            self.missing_combo.blockSignals(False)
            self.outlier_combo.blockSignals(False)
            self.invalid_type_combo.blockSignals(False)
            self.iqr_spin.blockSignals(False)

        pre_csv = os.path.join(folder, "preprocessed_data.csv")
        if os.path.exists(pre_csv):
            pre_df = pd.read_csv(pre_csv, encoding="utf-8-sig")
            self.populate_processed_preview(pre_df)

        eng_csv = os.path.join(folder, "engineered_data.csv")
        if os.path.exists(eng_csv):
            eng_df = pd.read_csv(eng_csv, encoding="utf-8-sig")
            self.engineered_preview_table.clear()
            self.engineered_preview_table.setRowCount(len(eng_df))
            self.engineered_preview_table.setColumnCount(len(eng_df.columns))
            self.engineered_preview_table.setHorizontalHeaderLabels([str(c) for c in eng_df.columns])
            for r, (_, row) in enumerate(eng_df.iterrows()):
                for c, val in enumerate(row):
                    text = "" if pd.isna(val) else f"{float(val):.4g}" if isinstance(val, (int, float, np.integer, np.floating)) else str(val)
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.engineered_preview_table.setItem(r, c, item)
            self.engineered_preview_table.resizeColumnsToContents()

        for img_file, canvas_fn in [
            ("training.png",    lambda img: self._show_image_on_canvas(self.canvas, img)),
            ("performance.png", lambda img: (self.perf_canvas.figure.clear(), self.perf_canvas.figure.add_subplot(111).imshow(img), self.perf_canvas.figure.axes[0].axis("off"), self.perf_canvas.draw())),
        ]:
            path = os.path.join(folder, img_file)
            if os.path.exists(path):
                canvas_fn(plt.imread(path))

        pred_mean = state.get("prediction_mean")
        pred_std = state.get("prediction_std")
        pred_inputs = state.get("prediction_inputs")
        if pred_mean and pred_std and pred_inputs:
            self._restore_prediction_display(pred_mean, pred_std, pred_inputs, "user")

        pre_mean = state.get("pretrained_prediction_mean")
        pre_std = state.get("pretrained_prediction_std")
        pre_inputs = state.get("pretrained_prediction_inputs")
        if pre_mean and pre_std and pre_inputs:
            self._restore_prediction_display(pre_mean, pre_std, pre_inputs, "pretrained")

        self.status_label.setText(f"상태: 분석 기록 '{name}' 복원 완료")

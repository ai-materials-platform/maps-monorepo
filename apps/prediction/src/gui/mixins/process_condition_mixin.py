"""공정 조건 예측기 GUI — ProcessConditionPanel(QWidget) + ProcessConditionMixin."""
import numpy as np
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from src.engine.process_condition_engine import (
    CORE_DEFAULTS,
    TARGETS,
    TARGET_DISPLAY,
    ProcessConditionEngine,
)
from src.gui.widgets import MplCanvas


class _PCTrainingThread(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)

    def __init__(self, engine: ProcessConditionEngine, extra_features: list):
        super().__init__()
        self.engine = engine
        self.extra_features = extra_features

    def run(self):
        try:
            self.progress.emit("데이터를 불러오는 중...")
            self.engine.load_data()
            n = len(self.engine.df_raw) if self.engine.df_raw is not None else 0
            self.progress.emit(f"데이터 로드 완료 ({n}개 샘플). 모델 학습 중...")
            results = self.engine.train(self.extra_features)
            self.finished.emit({'results': results, 'engine': self.engine})
        except Exception as exc:
            self.finished.emit(f"오류: {exc}")


class ProcessConditionPanel(QWidget):
    """공정 조건 예측기 패널 — 독립적으로 재사용 가능한 자급식 위젯."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = ProcessConditionEngine()
        self._extra_features: list[str] = []
        self._extra_widgets: dict[str, QLineEdit] = {}
        self._thread: _PCTrainingThread | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(4)
        splitter.addWidget(self._build_input_panel())
        splitter.addWidget(self._build_result_panel())
        splitter.setSizes([340, 820])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    def _build_input_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(380)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(10)

        # ── 핵심 공정 조건 그룹 ──
        core_group = QGroupBox("핵심 공정 조건")
        core_form = QFormLayout(core_group)
        core_form.setContentsMargins(12, 14, 12, 12)
        core_form.setHorizontalSpacing(12)
        core_form.setVerticalSpacing(8)
        core_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._core_inputs: dict[str, QLineEdit | None] = {}

        self._cooling_combo = QComboBox()
        self._cooling_combo.addItems(['0 — 로냉 (furnace)', '1 — 공냉 (air)', '2 — 수냉 (water)'])
        self._cooling_combo.setCurrentIndex(2)
        self._cooling_combo.currentIndexChanged.connect(self._sync_cooling)
        core_form.addRow(QLabel("냉각 방식"), self._cooling_combo)
        self._core_inputs['cooling_method'] = None

        text_fields = [
            ('solution_treatment_temp', '고용화 열처리 온도 (K)'),
            ('annealed',               '어닐링 여부 (0/1)'),
            ('tempered',               '템퍼링 여부 (0/1)'),
            ('quenched',               '급랭 여부 (0/1)'),
            ('Ni_eq',                  'Ni 당량 (Ni+30C+0.5Mn+...)'),
            ('Cr_eq',                  'Cr 당량 (Cr+Mo+1.5Si+...)'),
        ]
        for key, label in text_fields:
            le = QLineEdit(CORE_DEFAULTS.get(key, '0'))
            core_form.addRow(QLabel(label), le)
            self._core_inputs[key] = le

        content_layout.addWidget(core_group)

        # ── 추가 특성 그룹 ──
        self._extra_group = QGroupBox("추가 특성")
        extra_outer = QVBoxLayout(self._extra_group)
        extra_outer.setContentsMargins(12, 14, 12, 10)
        extra_outer.setSpacing(6)

        self._extra_form_widget = QWidget()
        self._extra_form_layout = QFormLayout(self._extra_form_widget)
        self._extra_form_layout.setContentsMargins(0, 0, 0, 0)
        self._extra_form_layout.setVerticalSpacing(6)
        self._extra_form_layout.setHorizontalSpacing(10)
        extra_outer.addWidget(self._extra_form_widget)

        add_btn = QPushButton("＋ 컬럼 추가")
        add_btn.setFixedHeight(30)
        add_btn.setStyleSheet(
            "QPushButton { background:#EEF6FF; color:#1D4ED8; border:1px solid #BFDBFE; "
            "border-radius:8px; font-size:11px; font-weight:700; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        add_btn.clicked.connect(self._open_add_feature_dialog)
        extra_outer.addWidget(add_btn)

        content_layout.addWidget(self._extra_group)
        content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # ── 테스트 데이터 버튼 ──
        test_btn = QPushButton("임의 테스트 데이터 입력")
        test_btn.setFixedHeight(34)
        test_btn.setStyleSheet(
            "QPushButton { background:#F1F5F9; color:#334155; border:1px solid #CBD5E1; "
            "border-radius:8px; font-size:11px; font-weight:600; }"
            "QPushButton:hover { background:#E2E8F0; }"
        )
        test_btn.clicked.connect(self._fill_test_data)
        outer.addWidget(test_btn)

        # ── 학습 버튼 ──
        self._train_btn = QPushButton("모델 학습")
        self._train_btn.setFixedHeight(42)
        self._train_btn.setStyleSheet(
            "QPushButton { background:#1D4ED8; color:white; border:none; "
            "border-radius:10px; font-size:13px; font-weight:700; }"
            "QPushButton:hover { background:#1E40AF; }"
            "QPushButton:disabled { background:#93C5FD; }"
        )
        self._train_btn.clicked.connect(self._on_train_clicked)
        outer.addWidget(self._train_btn)

        # ── 예측 버튼 ──
        self._predict_btn = QPushButton("물성 예측")
        self._predict_btn.setFixedHeight(42)
        self._predict_btn.setEnabled(False)
        self._predict_btn.setStyleSheet(
            "QPushButton { background:#16A34A; color:white; border:none; "
            "border-radius:10px; font-size:13px; font-weight:700; }"
            "QPushButton:hover { background:#15803D; }"
            "QPushButton:disabled { background:#86EFAC; }"
        )
        self._predict_btn.clicked.connect(self._on_predict_clicked)
        outer.addWidget(self._predict_btn)

        # ── 상태 레이블 ──
        self._status_label = QLabel("데이터 파일을 자동 탐색 후 학습합니다.")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("font-size:11px; color:#64748B; padding:4px 2px;")
        outer.addWidget(self._status_label)

        return panel

    def _build_result_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self._result_tabs = QTabWidget()

        # 탭 1 — 예측 결과
        pred_tab = QWidget()
        pred_layout = QVBoxLayout(pred_tab)
        pred_layout.setContentsMargins(14, 12, 14, 12)
        pred_layout.setSpacing(10)

        self._result_label = QLabel(
            "<b>예측 대기 중</b><br>왼쪽에서 모델을 학습한 뒤 물성 예측을 실행하세요."
        )
        self._result_label.setWordWrap(True)
        self._result_label.setStyleSheet("font-size:13px; color:#334155;")
        pred_layout.addWidget(self._result_label)

        self._pred_canvas = MplCanvas(self, width=5, height=3, dpi=100)
        pred_layout.addWidget(self._pred_canvas, 1)
        self._result_tabs.addTab(pred_tab, "예측 결과")

        # 탭 2 — 모델 성능 비교 (스크롤 가능)
        perf_tab = QWidget()
        perf_tab_layout = QVBoxLayout(perf_tab)
        perf_tab_layout.setContentsMargins(0, 0, 0, 0)
        perf_tab_layout.setSpacing(0)

        perf_scroll = QScrollArea()
        perf_scroll.setWidgetResizable(True)
        perf_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        perf_content = QWidget()
        perf_layout = QVBoxLayout(perf_content)
        perf_layout.setContentsMargins(14, 12, 14, 12)
        perf_layout.setSpacing(10)

        self._model_status_label = QLabel(
            "<b>모델 미학습</b><br>학습을 실행하면 4개 모델 비교 결과가 표시됩니다."
        )
        self._model_status_label.setWordWrap(True)
        self._model_status_label.setStyleSheet("font-size:12px; color:#334155;")
        perf_layout.addWidget(self._model_status_label)

        self._perf_canvas = MplCanvas(self, width=6, height=4, dpi=100)
        self._perf_canvas.setMinimumHeight(400)
        perf_layout.addWidget(self._perf_canvas)
        perf_layout.addStretch()

        perf_scroll.setWidget(perf_content)
        perf_tab_layout.addWidget(perf_scroll, 1)
        self._result_tabs.addTab(perf_tab, "모델 성능 비교")

        # 탭 3 — 특성 중요도
        fi_tab = QWidget()
        fi_layout = QVBoxLayout(fi_tab)
        fi_layout.setContentsMargins(14, 12, 14, 12)

        self._fi_label = QLabel("학습 후 최적 모델의 특성 중요도가 표시됩니다.")
        self._fi_label.setStyleSheet("font-size:12px; color:#64748B;")
        fi_layout.addWidget(self._fi_label)

        self._fi_canvas = MplCanvas(self, width=5, height=3, dpi=100)
        fi_layout.addWidget(self._fi_canvas, 1)
        self._result_tabs.addTab(fi_tab, "특성 중요도")

        layout.addWidget(self._result_tabs, 1)
        return panel

    # ------------------------------------------------------------------
    # 냉각 방식 동기화
    # ------------------------------------------------------------------

    def _sync_cooling(self, index: int):
        annealed = self._core_inputs.get('annealed')
        quenched = self._core_inputs.get('quenched')
        if annealed:
            annealed.setText('1' if index == 0 else '0')
        if quenched:
            quenched.setText('1' if index == 2 else '0')

    # ------------------------------------------------------------------
    # 입력값 수집
    # ------------------------------------------------------------------

    def _get_input_dict(self) -> dict:
        d: dict[str, float] = {}
        for key, widget in self._core_inputs.items():
            if widget is None:
                continue
            try:
                d[key] = float(widget.text())
            except (ValueError, AttributeError):
                d[key] = 0.0
        d['cooling_method'] = float(self._cooling_combo.currentIndex())
        for key, widget in self._extra_widgets.items():
            try:
                d[key] = float(widget.text())
            except (ValueError, AttributeError):
                d[key] = 0.0
        return d

    # ------------------------------------------------------------------
    # 임의 테스트 데이터 (316 SS 기준)
    # ------------------------------------------------------------------

    def _fill_test_data(self):
        test_values = {
            'solution_treatment_temp': '1323',
            'annealed': '0',
            'tempered': '0',
            'quenched': '1',
            'Ni_eq': '13.5',
            'Cr_eq': '19.7',
        }
        for key, val in test_values.items():
            widget = self._core_inputs.get(key)
            if widget:
                widget.setText(val)
        self._cooling_combo.setCurrentIndex(2)
        self._status_label.setText(
            "임의 테스트 데이터 입력 완료 (316 SS 기준). 학습 후 예측 실행 가능."
        )

    # ------------------------------------------------------------------
    # 추가 특성 관리
    # ------------------------------------------------------------------

    def _open_add_feature_dialog(self):
        try:
            available = self._engine.get_available_extra_features()
        except Exception as exc:
            self._status_label.setText(f"데이터 로드 오류: {exc}")
            return

        already = set(self._extra_features)
        dlg = QDialog(self)
        dlg.setWindowTitle("추가 특성 선택")
        dlg.resize(360, 440)
        layout = QVBoxLayout(dlg)

        info = QLabel("학습/예측에 추가로 사용할 컬럼을 선택하세요.\n(데이터 파일에 존재하는 컬럼만 표시)")
        info.setWordWrap(True)
        info.setStyleSheet("font-size:12px; margin-bottom:6px;")
        layout.addWidget(info)

        list_widget = QListWidget()
        for col in available:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if col in already else Qt.CheckState.Unchecked
            )
            list_widget.addItem(item)
        layout.addWidget(list_widget, 1)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = [
                list_widget.item(i).text()
                for i in range(list_widget.count())
                if list_widget.item(i).checkState() == Qt.CheckState.Checked
            ]
            self._extra_features = selected
            self._refresh_extra_ui()

    def _refresh_extra_ui(self):
        while self._extra_form_layout.rowCount() > 0:
            self._extra_form_layout.removeRow(0)
        self._extra_widgets = {}

        for feat in self._extra_features:
            le = QLineEdit('0')

            def _make_remove(f=feat):
                def _remove():
                    self._extra_features = [x for x in self._extra_features if x != f]
                    self._refresh_extra_ui()
                return _remove

            rm_btn = QPushButton('×')
            rm_btn.setFixedSize(26, 26)
            rm_btn.setStyleSheet(
                "QPushButton { background:#FEE2E2; color:#DC2626; border:none; "
                "border-radius:4px; font-weight:700; }"
                "QPushButton:hover { background:#FECACA; }"
            )
            rm_btn.clicked.connect(_make_remove())

            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(4)
            row_l.addWidget(le, 1)
            row_l.addWidget(rm_btn)

            self._extra_form_layout.addRow(QLabel(feat), row_w)
            self._extra_widgets[feat] = le

    # ------------------------------------------------------------------
    # 학습
    # ------------------------------------------------------------------

    def _on_train_clicked(self):
        self._train_btn.setEnabled(False)
        self._predict_btn.setEnabled(False)
        self._status_label.setText("학습 중... 잠시만 기다려 주세요.")

        self._thread = _PCTrainingThread(self._engine, list(self._extra_features))
        self._thread.progress.connect(self._status_label.setText)
        self._thread.finished.connect(self._on_training_finished)
        self._thread.start()

    def _on_training_finished(self, result):
        self._train_btn.setEnabled(True)

        if isinstance(result, str):
            self._status_label.setText(result)
            return

        results: dict = result['results']
        engine: ProcessConditionEngine = result['engine']
        best = engine.best_model_name
        best_r2 = results[best]['r2_avg']
        best_mae = results[best]['mae_avg']

        self._predict_btn.setEnabled(True)
        self._status_label.setText(
            f"학습 완료 ★ {best}  R²={best_r2:.4f}  MAE={best_mae:.2f}"
        )

        lines = [f"<b>모델 비교 결과 — 최적: {best}</b><br><br>"]
        for name, res in results.items():
            star = "★ " if name == best else "　 "
            lines.append(
                f"<b>{star}{name}</b>: 평균 R²={res['r2_avg']:.4f}, 평균 MAE={res['mae_avg']:.2f}<br>"
            )
            for i, t in enumerate(engine.used_targets):
                short = TARGET_DISPLAY[TARGETS.index(t)] if t in TARGETS else t
                lines.append(
                    f"&nbsp;&nbsp;&nbsp;{short}: R²={res['r2_per_target'][i]:.4f}, "
                    f"MAE={res['mae_per_target'][i]:.2f}<br>"
                )
        self._model_status_label.setText("".join(lines))

        self._draw_model_comparison(results, engine)
        self._draw_feature_importance(engine)
        self._result_tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # 차트 — 모델 성능 비교
    # ------------------------------------------------------------------

    def _draw_model_comparison(self, results: dict, engine: ProcessConditionEngine):
        ax = self._perf_canvas.axes
        ax.clear()

        model_names = list(results.keys())
        n_t = len(engine.used_targets)
        labels = [TARGET_DISPLAY[TARGETS.index(t)] if t in TARGETS else t for t in engine.used_targets]
        x = np.arange(n_t)
        w = 0.8 / max(len(model_names), 1)
        palette = ['#3B82F6', '#F59E0B', '#10B981', '#EF4444']

        for i, name in enumerate(model_names):
            r2s = results[name]['r2_per_target']
            offset = (i - len(model_names) / 2 + 0.5) * w
            bars = ax.bar(x + offset, r2s, w * 0.88, label=name,
                          color=palette[i % len(palette)], alpha=0.85)
            for bar in bars:
                h = bar.get_height()
                if h > 0.1:
                    ax.text(bar.get_x() + bar.get_width() / 2, h + 0.01, f'{h:.2f}',
                            ha='center', va='bottom', fontsize=7)

        best = max(results, key=lambda k: results[k]['r2_avg'])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel('R² Score')
        ax.set_ylim(0, 1.18)
        ax.set_title(f'모델 성능 비교 (최적: {best})', fontsize=11, fontweight='bold')
        ax.legend(fontsize=8, loc='lower right')
        ax.grid(axis='y', linestyle=':', alpha=0.5)
        self._perf_canvas.figure.tight_layout(pad=0.4)
        self._perf_canvas.draw()

    # ------------------------------------------------------------------
    # 차트 — 특성 중요도
    # ------------------------------------------------------------------

    def _draw_feature_importance(self, engine: ProcessConditionEngine):
        imp = engine.get_feature_importance()
        if not imp:
            self._fi_label.setText("이 모델은 특성 중요도를 지원하지 않습니다.")
            return

        self._fi_label.setText("")
        ax = self._fi_canvas.axes
        ax.clear()

        items = sorted(imp.items(), key=lambda kv: kv[1], reverse=True)
        feats, vals = zip(*items)
        max_v = max(vals)
        colors = ['#E56020' if v == max_v else '#3B82F6' for v in vals]

        ax.barh(list(feats), list(vals), color=colors, alpha=0.85)
        ax.set_xlabel('상대적 중요도')
        ax.set_title(f'특성 중요도 ({engine.best_model_name})', fontsize=11, fontweight='bold')
        ax.invert_yaxis()
        ax.grid(axis='x', linestyle=':', alpha=0.5)
        self._fi_canvas.figure.tight_layout(pad=0.4)
        self._fi_canvas.draw()

    # ------------------------------------------------------------------
    # 예측
    # ------------------------------------------------------------------

    def _on_predict_clicked(self):
        try:
            input_dict = self._get_input_dict()
            pred = self._engine.predict(input_dict)
        except Exception as exc:
            self._result_label.setText(f"<b>예측 오류</b><br>{exc}")
            return

        values = [pred.get(t, 0.0) for t in self._engine.used_targets]
        labels = [
            TARGET_DISPLAY[TARGETS.index(t)] if t in TARGETS else t
            for t in self._engine.used_targets
        ]

        cooling_names = ['로냉', '공냉', '수냉']
        cooling_idx = int(input_dict.get('cooling_method', 0))
        cooling_str = cooling_names[cooling_idx] if 0 <= cooling_idx <= 2 else str(cooling_idx)

        lines = [
            f"<b>물성 예측 결과  ({self._engine.best_model_name})</b><br><br>",
            "<b>강도</b><br>",
        ]
        for lbl, val in zip(labels[:2], values[:2]):
            lines.append(f"&nbsp;&nbsp;{lbl}: <b>{val:.1f}</b><br>")
        lines.append("<br><b>연성</b><br>")
        for lbl, val in zip(labels[2:], values[2:]):
            lines.append(f"&nbsp;&nbsp;{lbl}: <b>{val:.2f}</b><br>")
        lines.append(
            f"<br><span style='color:#64748B; font-size:11px;'>"
            f"입력 — 온도: {input_dict.get('solution_treatment_temp', 0):.0f} K, "
            f"냉각: {cooling_str}, "
            f"Ni당량: {input_dict.get('Ni_eq', 0):.2f}, "
            f"Cr당량: {input_dict.get('Cr_eq', 0):.2f}"
            f"</span>"
        )
        self._result_label.setText("".join(lines))
        self._draw_prediction_chart(values, labels)
        self._result_tabs.setCurrentIndex(0)

    def _draw_prediction_chart(self, values: list, labels: list):
        ax = self._pred_canvas.axes
        ax.clear()
        palette = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B']
        ax.bar(labels, values, color=palette[:len(values)], alpha=0.85)
        ax.set_ylabel('예측값')
        ax.set_title(
            f'물성 예측 결과  ({self._engine.best_model_name})',
            fontsize=11, fontweight='bold'
        )
        for i, v in enumerate(values):
            ax.text(i, v * 1.02 if v > 0 else 0.5, f'{v:.1f}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax.grid(axis='y', linestyle=':', alpha=0.5)
        self._pred_canvas.figure.tight_layout(pad=0.4)
        self._pred_canvas.draw()


class ProcessConditionMixin:
    """공정 조건 예측기 탭을 MainWindow User 페이지에 추가하는 믹스인."""

    def setup_process_condition_tab(self):
        panel = ProcessConditionPanel()
        self.tabs.addTab(panel, "공정 조건 예측기")
        self._pc_panel = panel

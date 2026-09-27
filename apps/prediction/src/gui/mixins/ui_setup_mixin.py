import matplotlib.pyplot as plt
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMenu,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.constants import APP_FONT_SIZE, GLOBAL_QSS
from src.gui.widgets import CustomTitleBar, FloatingChatbotIcon, MAPSLogoWidget, MplCanvas, PredictionGuideOverlay



class UISetupMixin:
    _COMPOSITION_KEYS = ["Fe", "C", "Si", "Mn", "P", "S", "Ni", "Cr", "Mo", "Cu", "V", "N", "Nb", "Ti", "B", "Al"]
    _PRETRAINED_EXTRA_FEATURE_ORDER = [
        "Solution_treatment_time(s)",
        "Grains mm-2",
        "Type of melting",
        "Size of ingot",
        "Product form",
        "Temperature (K)",
        "Ni_eq",
        "Cr_eq",
        "Cr_Ni_ratio",
        "C_plus_N",
    ]
    _PRETRAINED_EXTRA_FEATURE_DEFAULTS = {
        "Solution_treatment_time(s)": "3600",
        "Grains mm-2": "500",
        "Type of melting": "2",
        "Size of ingot": "50",
        "Product form": "3",
        "Temperature (K)": "300",
        "Ni_eq": "0.0",
        "Cr_eq": "0.0",
        "Cr_Ni_ratio": "0.0",
        "C_plus_N": "0.0",
    }
    _PRETRAINED_EXTRA_FEATURE_LABELS = {
        "Solution_treatment_time(s)": "고용화 열처리 시간 (s)",
        "Grains mm-2": "결정립 수 (mm^-2)",
        "Type of melting": "용해 방식",
        "Size of ingot": "잉곳 크기",
        "Product form": "제품 형상",
        "Temperature (K)": "시험 온도 (K)",
        "Ni_eq": "Ni 당량",
        "Cr_eq": "Cr 당량",
        "Cr_Ni_ratio": "Cr/Ni 비율",
        "C_plus_N": "C+N",
    }
    _PRETRAINED_CALCULATED_FEATURES = {"Ni_eq", "Cr_eq", "Cr_Ni_ratio", "C_plus_N"}
    _FIELD_TOOLTIPS = {
        # 합금 조성
        "Fe": "철 (Iron)\n오스테나이트계 스테인리스강의 주 성분.\n일반적으로 60~70 wt% 이상.",
        "C":  "탄소 (Carbon)\n강도를 높이지만 내식성을 낮춤.\n스테인리스강에서는 0.03~0.15 wt% 수준.",
        "Si": "규소 (Silicon)\n탈산제 및 고온 내산화성 향상.\n통상 0.3~1.0 wt%.",
        "Mn": "망간 (Manganese)\n오스테나이트 안정화 원소.\n일반적으로 1.0~2.0 wt%.",
        "P":  "인 (Phosphorus)\n불순물 원소. 취성 유발.\n0.045 wt% 이하로 관리.",
        "S":  "황 (Sulfur)\n불순물 원소. 열간 가공성 저하.\n0.03 wt% 이하로 관리.",
        "Ni": "니켈 (Nickel)\n오스테나이트 안정화 핵심 원소.\n300계열 기준 8~12 wt%.",
        "Cr": "크롬 (Chromium)\n내식성 부여 핵심 원소 (부동태 피막 형성).\n16~18 wt% 수준.",
        "Mo": "몰리브덴 (Molybdenum)\n공식(pitting) 내식성 향상.\nSUS316 기준 2~3 wt%.",
        "Cu": "구리 (Copper)\n내식성 및 가공성 향상에 기여.\n보통 0~3 wt%.",
        "V":  "바나듐 (Vanadium)\n탄화물 형성으로 강도 향상.\n0.1~0.5 wt% 수준.",
        "N":  "질소 (Nitrogen)\n고용강화 및 오스테나이트 안정화. Ni 대체 효과.\n0~0.25 wt%.",
        "Nb": "니오브 (Niobium)\n탄화물 안정화로 입계부식 방지.\n0.01~0.1 wt%.",
        "Ti": "티타늄 (Titanium)\n탄소 고정으로 예민화(sensitization) 방지.\n0.01~0.4 wt%.",
        "B":  "붕소 (Boron)\n열간 가공성 개선. 미량 첨가.\n0.001~0.005 wt%.",
        "Al": "알루미늄 (Aluminum)\n탈산 및 내산화성 향상.\n통상 0.01~0.05 wt%.",
        # 합금 지표 (자동 계산)
        "Ni_eq": "Ni 당량 (Nickel Equivalent)\n오스테나이트 형성 경향 지수.\n수식: Ni + 30×C + 0.5×Mn + 30×N + 0.3×Cu\n값이 클수록 오스테나이트 상 안정.",
        "Cr_eq": "Cr 당량 (Chromium Equivalent)\n페라이트 형성 경향 지수.\n수식: Cr + Mo + 1.5×Si + 0.5×Nb\n값이 클수록 페라이트/마르텐사이트 상 경향.",
        "Cr_Ni_ratio": "Cr/Ni 비율\n조직 균형 지수.\nCr_eq / Ni_eq 비율로 Schaeffler 상 도표에서 조직 예측에 사용.",
        "C_plus_N": "침입형 원소 합 (C+N)\n고용강화 및 고온 강도에 직접 영향.\n값이 클수록 항복강도↑, 내식성 저하 가능.",
        # 공정 및 조직
        "Solution_treatment_temperature": "고용화 열처리 온도 (K)\n탄화물을 기지에 재용해시키는 열처리 온도.\n일반적으로 1323~1423 K (1050~1150 °C).",
        "Solution_treatment_time(s)":     "고용화 열처리 시간 (초)\n열처리 유지 시간. 두꺼운 제품일수록 길게 필요.\n일반적으로 1800~7200초 (30분~2시간).",
        "Grains mm-2":   "결정립 수 (mm⁻²)\n단위 면적당 결정립 수. 값이 클수록 결정립 미세.\n미세 결정립 → 강도↑, 인성↑.",
        "Type of melting": "용해 방식\n0=전기로(EAF), 1=유도용해, 2=AOD, 3=VOD 등.\n정수 코드로 입력.",
        "Size of ingot":  "잉곳 크기 (mm 단위)\n주조 잉곳의 크기. 응고 속도·편석에 영향.",
        "Product form":   "제품 형상\n0=판재, 1=봉재, 2=관재, 3=단조품 등.\n정수 코드로 입력.",
        "Temperature (K)": "시험 온도 (K)\n물성을 측정한 온도. 상온은 298 K.\n고온 특성이 필요한 경우 실제 사용 온도 입력.",
    }

    def init_ui(self):
        self.setStyleSheet(GLOBAL_QSS)
        self._apply_ui_font()

        # 네이티브 메뉴바 숨김 — 커스텀 타이틀바에 통합
        self.menuBar().hide()

        from PyQt6.QtWidgets import QMenu  # noqa: PLC0415
        file_menu = QMenu("파일", self)
        file_menu.addAction("분석 기록 저장", self._save_workspace_from_menu)
        file_menu.addAction("분석 기록 불러오기", self._open_workspace_dialog)
        file_menu.addSeparator()
        file_menu.addAction("프로젝트 닫기", self.close)
        help_menu = QMenu("도움말", self)
        help_menu.addAction("사용자 가이드",
                            lambda: self._show_prediction_guide(self.material_prediction_page))
        self._custom_menus = (
            [("파일", file_menu)]
            + [(n, QMenu(n, self)) for n in ["편집", "보기", "데이터", "분석", "도구"]]
            + [("도움말", help_menu)]
        )

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._custom_titlebar = CustomTitleBar(self, self._custom_menus)
        root_layout.addWidget(self._custom_titlebar)
        root_layout.addWidget(self._create_toolbar())

        self.main_mode_stack = QStackedWidget()
        root_layout.addWidget(self.main_mode_stack, 1)

        self.material_prediction_page = self._create_material_prediction_page()
        self.main_mode_stack.addWidget(self.material_prediction_page)

        self.user_page = QWidget()
        user_layout = QVBoxLayout(self.user_page)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)

        splitter.addWidget(self._create_left_panel())
        splitter.addWidget(self._create_settings_panel())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        splitter.addWidget(self.tabs)
        splitter.setSizes([190, 300, 860])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 1)

        user_layout.addWidget(splitter, 1)
        self.main_mode_stack.addWidget(self.user_page)
        self._switch_main_mode(0)

        sb = self.statusBar()
        self._sb_status = QLabel("● 준비완료")
        self._sb_samples = QLabel("샘플: —")
        self._sb_missing = QLabel("결측: —")
        self._sb_model = QLabel("모델: 미훈련")
        sb.addWidget(self._sb_status)
        sb.addWidget(self._sb_samples)
        sb.addWidget(self._sb_missing)
        sb.addWidget(self._sb_model)

        self.setup_preprocessing_tab()
        self.setup_feature_selection_tab()
        self.setup_training_tab()
        self.setup_performance_tab()
        self.setup_inference_tab()
        self.setup_workspace_tab()
        self.refresh_workspace_list()
        self._apply_theme_colors()
        self.prepare_pretrained_model()

        # 모든 버튼에 포인터 커서 적용
        for btn in self.findChildren(QPushButton):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        from PyQt6.QtCore import QTimer  # noqa: PLC0415
        # 프레임리스 창에서 자식 위젯 이벤트 문제 회피 → 독립 Tool 창으로 생성
        self._floating_chatbot = FloatingChatbotIcon()
        self._floating_chatbot.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self._floating_chatbot.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._floating_chatbot.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._floating_chatbot.set_bounds_window(self)
        self._floating_chatbot.clicked.connect(self.toggle_llm_chat_dialog)
        self._floating_chatbot_placed = False  # 초기 배치 여부 플래그
        self._floating_chatbot.show()
        QTimer.singleShot(0, self._reposition_floating_chatbot)

    def _apply_ui_font(self):
        # pixelSize → pointSize 변환 (DPI 기반) — setPixelSize 사용 시 pointSize=-1 경고 방지
        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen else 96.0
        pt_size = max(1.0, self._ui_font_size * 72.0 / dpi)

        font = QFont(self._ui_font_family)
        font.setPointSizeF(pt_size)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        QApplication.instance().setFont(font)
        self.setFont(font)
        plt.rcParams["font.family"] = ["Malgun Gothic", "sans-serif"]
        if hasattr(self, "canvas"):
            self.render_training_placeholder()
        if hasattr(self, "perf_canvas"):
            self.render_performance_placeholder()

    def _create_toolbar(self):
        bar = QWidget()
        self._toolbar_widget = bar
        bar.setFixedHeight(48)
        bar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #C9D2DC;")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 14, 0)
        layout.setSpacing(12)

        # --- 네비게이션 버튼 ---
        nav_style_sim = (
            "QPushButton { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; "
            "border-radius: 6px; font-size: 11px; font-weight: 700; padding: 0 10px; height: 28px; }"
            "QPushButton:hover { background: #DBEAFE; }"
        )
        self._nav_sim_btn = QPushButton("시뮬레이션 ↗")
        self._nav_sim_btn.setFixedHeight(28)
        self._nav_sim_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nav_sim_btn.setStyleSheet(nav_style_sim)
        self._nav_sim_btn.clicked.connect(self._open_simulation_app)
        layout.addWidget(self._nav_sim_btn)

        nav_div = QWidget()
        nav_div.setFixedSize(1, 24)
        nav_div.setStyleSheet("background: #CBD5E1;")
        layout.addWidget(nav_div)

        self._seg_container = QWidget()
        self._seg_container.setFixedHeight(32)
        seg_layout = QHBoxLayout(self._seg_container)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(0)

        self.material_mode_btn = QPushButton("물성예측")
        self.material_mode_btn.setCheckable(True)
        self.material_mode_btn.setFixedHeight(28)
        self.material_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.material_mode_btn.clicked.connect(lambda: self._switch_main_mode(0))
        seg_layout.addWidget(self.material_mode_btn)

        self.user_mode_btn = QPushButton("데이터 학습")
        self.user_mode_btn.setCheckable(True)
        self.user_mode_btn.setFixedHeight(28)
        self.user_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_mode_btn.clicked.connect(lambda: self._switch_main_mode(1))
        seg_layout.addWidget(self.user_mode_btn)

        layout.addWidget(self._seg_container)
        layout.addStretch()

        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        self._toolbar_title = QLabel("MAPS")
        self._toolbar_title.setStyleSheet(
            "color: #111827; font-size: 16px; font-weight: 800; letter-spacing: 0.5px;"
        )
        self._toolbar_subtitle = QLabel("Microstructure & Alloy Prediction System")
        self._toolbar_subtitle.setStyleSheet(
            "color: #64748B; font-size: 9px; font-weight: 500; letter-spacing: 0.3px;"
        )
        title_layout.addWidget(self._toolbar_title)
        title_layout.addWidget(self._toolbar_subtitle)

        brand_widget = QWidget()
        brand_layout = QHBoxLayout(brand_widget)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(8)
        brand_layout.addWidget(MAPSLogoWidget(size=40))
        brand_layout.addWidget(title_widget)
        layout.addWidget(brand_widget)

        self._theme_btn = QPushButton("다크 모드")
        self._theme_btn.setFixedHeight(32)
        self._theme_btn.setMinimumWidth(92)
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setStyleSheet(
            "QPushButton { background: #111827; color: #F8FAFC; border: 1px solid #111827; "
            "border-radius: 16px; font-size: 11px; font-weight: 700; padding: 0 14px; }"
            "QPushButton:hover { background: #1F2937; border-color: #334155; }"
        )
        self._theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self._theme_btn)
        self._update_mode_buttons()
        return bar

    def _open_simulation_app(self):
        import subprocess
        import os
        from pathlib import Path
        from PyQt6.QtWidgets import QMessageBox
        sim_dir = os.environ.get(
            "AI_MATERIALS_SIMULATION_DIR",
            str(Path(__file__).parents[4] / "ai-materials-discovery-platform-simulation"),
        )
        if not Path(sim_dir).exists():
            QMessageBox.warning(self, "경로 없음", f"시뮬레이션 레포를 찾을 수 없습니다:\n{sim_dir}")
            return
        npm = "npm.cmd" if os.name == "nt" else "npm"
        kwargs = {"cwd": sim_dir, "shell": False, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen([npm, "run", "dev"], **kwargs)

    def _switch_main_mode(self, index):
        if hasattr(self, "main_mode_stack"):
            self.main_mode_stack.setCurrentIndex(index)
        self._current_main_mode = index
        self._update_mode_buttons()

    def _update_mode_buttons(self):
        if not hasattr(self, "material_mode_btn") or not hasattr(self, "user_mode_btn"):
            return
        current_index = getattr(self, "_current_main_mode", 0)
        self.material_mode_btn.setChecked(current_index == 0)
        self.user_mode_btn.setChecked(current_index == 1)
        self._apply_mode_button_styles()

    def _apply_mode_button_styles(self):
        d = self._dark_mode
        if hasattr(self, "_seg_container"):
            container_bg     = "#2F3339" if d else "#F1F5F9"
            container_border = "#4F5965" if d else "#CBD5E1"
            self._seg_container.setStyleSheet(
                f"QWidget {{ background: {container_bg}; border: 1px solid {container_border}; border-radius: 16px; }}"
            )
        inactive_text = "#D5DBE3" if d else "#64748B"
        active_bg    = "#3A4048" if d else "#FFFFFF"
        active_text  = "#F3F4F6" if d else "#111827"
        hover_bg = "rgba(255,255,255,20)" if d else "rgba(0,0,0,13)"
        btn_style = (
            f"QPushButton {{ background: transparent; color: {inactive_text}; border: none; "
            "border-radius: 14px; font-size: 11px; font-weight: 700; padding: 0 16px; min-height: 28px; }"
            f"QPushButton:checked {{ background: {active_bg}; color: {active_text}; }}"
            f"QPushButton:hover:!checked {{ background: {hover_bg}; }}"
        )
        if hasattr(self, "material_mode_btn"):
            self.material_mode_btn.setStyleSheet(btn_style)
        if hasattr(self, "user_mode_btn"):
            self.user_mode_btn.setStyleSheet(btn_style)

    def _create_material_prediction_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._mp_mode_tabs = QTabWidget()
        self._mp_mode_tabs.setDocumentMode(True)
        corner_widget = QWidget()
        corner_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        corner_widget.setFixedHeight(36)
        self._mp_prediction_guide_corner = corner_widget
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 10, 0)
        corner_layout.setSpacing(0)
        corner_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._mp_prediction_guide_btn = QPushButton("사용자 가이드")
        self._mp_prediction_guide_btn.setFixedHeight(28)
        self._mp_prediction_guide_btn.setStyleSheet(
            "QPushButton { background: #EEF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; "
            "border-radius: 14px; font-size: 11px; font-weight: 700; padding: 0 14px; }"
            "QPushButton:hover { background: #DBEAFE; }"
        )
        self._mp_prediction_guide_btn.clicked.connect(lambda: self._show_prediction_guide(page))
        corner_layout.addWidget(self._mp_prediction_guide_btn)
        self._mp_mode_tabs.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)
        corner_widget.hide()
        corner_widget.setFixedSize(0, 0)
        self._mp_prediction_guide_btn.hide()

        # ── 탭 1: 사전학습 예측 ──
        pretrained_tab = QWidget()
        pretrained_layout = QVBoxLayout(pretrained_tab)
        pretrained_layout.setContentsMargins(12, 12, 12, 12)
        pretrained_layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.addStretch()
        guide_btn = QPushButton("사용 가이드")
        guide_btn.setFixedHeight(30)
        guide_btn.setStyleSheet(
            "QPushButton { background: #EEF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; "
            "border-radius: 14px; font-size: 11px; font-weight: 700; padding: 0 14px; }"
            "QPushButton:hover { background: #DBEAFE; }"
        )
        guide_btn.clicked.connect(lambda: self._show_prediction_guide(page))
        top_row.addWidget(guide_btn)
        pretrained_layout.addLayout(top_row)
        guide_btn.hide()
        pretrained_layout.takeAt(pretrained_layout.count() - 1)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(4)

        input_card = QGroupBox("사전학습 모델 입력")
        input_layout = QVBoxLayout(input_card)
        self.pretrained_active_model_info = QLabel("사용 중인 모델: 사전학습 모델 없음")
        self.pretrained_active_model_info.hide()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)

        self.pretrained_inputs = {}
        self._pretrained_extra_feature_names = []
        self._pretrained_extra_feature_widgets = {}
        self._pretrained_extra_feature_labels = []
        self._pretrained_extra_feature_fields = []
        self._build_pretrained_prediction_input_sections(form_layout, self.pretrained_inputs)
        self._setup_fe_auto_update(self.pretrained_inputs)
        scroll.setWidget(form_container)
        input_layout.addWidget(scroll, 1)

        self.pretrained_predict_btn = QPushButton("사전학습 모델로 예측")
        self.pretrained_predict_btn.setFixedHeight(42)
        self.pretrained_predict_btn.setStyleSheet(
            "QPushButton { background: #16A34A; color: white; border: none; border-radius: 10px; font-weight: 700; }"
            "QPushButton:hover { background: #15803D; }"
        )
        self.pretrained_predict_btn.clicked.connect(self.on_pretrained_predict_clicked)
        input_layout.addWidget(self.pretrained_predict_btn)
        input_card.setMinimumWidth(280)
        content_splitter.addWidget(input_card)

        result_card = QGroupBox("예측 결과")
        result_layout = QVBoxLayout(result_card)
        self.pretrained_result_tabs = QTabWidget()

        result_tab = QWidget()
        result_tab_layout = QVBoxLayout(result_tab)
        self.pretrained_result_display = QLabel(
            "<b>예측 준비 완료</b><br>사전학습 모델로 바로 물성 예측을 실행할 수 있습니다."
        )
        self.pretrained_result_display.setWordWrap(True)
        result_tab_layout.addWidget(self.pretrained_result_display)
        self.pretrained_export_btn = QPushButton("CSV로 내보내기")
        self.pretrained_export_btn.setFixedHeight(28)
        self.pretrained_export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pretrained_export_btn.setEnabled(False)
        self.pretrained_export_btn.clicked.connect(
            lambda: self._export_prediction_csv("_pretrained_prediction_state")
        )
        result_tab_layout.addWidget(self.pretrained_export_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.pretrained_prediction_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        result_tab_layout.addWidget(self.pretrained_prediction_canvas)
        self.pretrained_result_tabs.addTab(result_tab, "예측 결과")

        curve_tab = QWidget()
        curve_layout = QVBoxLayout(curve_tab)
        curve_layout.addWidget(
            self._create_curve_info_panel(
                "pretrained_curve_placeholder",
                "pretrained_curve_legend_card",
            )
        )
        self._pretrained_explore_btn = QPushButton("자세하게 보기")
        self._pretrained_explore_btn.setFixedHeight(30)
        self._pretrained_explore_btn.setStyleSheet(
            "QPushButton { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; "
            "border-radius: 6px; font-size: 11px; font-weight: 600; padding: 0 12px; }"
            "QPushButton:hover { background: #E2E8F0; }"
        )
        self._pretrained_explore_btn.clicked.connect(lambda: self._open_strain_explore_dialog("pretrained"))
        curve_layout.addWidget(self._pretrained_explore_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.pretrained_curve_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        curve_layout.addWidget(self.pretrained_curve_canvas)
        self.pretrained_result_tabs.addTab(curve_tab, "Stress-Strain Curve")

        result_layout.addWidget(self.pretrained_result_tabs)
        self.render_prediction_placeholder(
            self.pretrained_prediction_canvas,
            "사전학습 예측 결과",
            title_fontsize=12.5,
            body_fontsize=9.8,
        )
        self.render_stress_strain_placeholder(
            self.pretrained_curve_canvas,
            self.pretrained_curve_placeholder,
        )

        self.pretrained_status_label = QLabel("")
        self.pretrained_status_label.setWordWrap(True)
        self.pretrained_status_label.hide()

        self.pretrained_model_summary_label = QLabel("")
        self.pretrained_model_summary_label.setWordWrap(True)
        self.pretrained_model_summary_label.hide()
        content_splitter.addWidget(result_card)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([340, 900])

        pretrained_layout.addWidget(content_splitter, 1)
        self._mp_mode_tabs.addTab(pretrained_tab, "사전학습 예측")

        # ── 탭 2: 공정 조건 예측기 ──

        outer.addWidget(self._mp_mode_tabs, 1)
        return page

    def _build_pretrained_prediction_input_sections(self, parent_layout, input_store):
        comp_group = QGroupBox("합금 조성 (wt%)")
        comp_group_layout = QVBoxLayout(comp_group)
        comp_group_layout.setContentsMargins(12, 12, 12, 12)
        comp_group_layout.setSpacing(12)
        composition_defaults = {
            "Fe": "96.0",
            "C": "0.08",
            "Si": "0.4",
            "Mn": "1.5",
            "P": "0.01",
            "S": "0.005",
            "Ni": "0.2",
            "Cr": "0.3",
            "Mo": "0.05",
            "Cu": "0.1",
            "V": "0.01",
            "N": "0.005",
            "Nb": "0.02",
            "Ti": "0.01",
            "B": "0.0005",
            "Al": "0.03",
        }
        composition_items = list(composition_defaults.items())
        midpoint = (len(composition_items) + 1) // 2
        comp_columns = QHBoxLayout()
        comp_columns.setContentsMargins(0, 0, 0, 0)
        comp_columns.setSpacing(16)
        comp_columns.addLayout(self._create_prediction_form(composition_items[:midpoint], input_store))
        comp_columns.addLayout(self._create_prediction_form(composition_items[midpoint:], input_store))
        comp_group_layout.addLayout(comp_columns)

        reset_row = QHBoxLayout()
        reset_row.addStretch()
        self._pretrained_reset_btn = QPushButton("기본값으로 초기화")
        self._pretrained_reset_btn.setFixedHeight(26)
        self._pretrained_reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pretrained_reset_btn.clicked.connect(self._reset_pretrained_inputs)
        reset_row.addWidget(self._pretrained_reset_btn)
        comp_group_layout.addLayout(reset_row)

        parent_layout.addWidget(comp_group)
        self._prediction_input_groups.append(comp_group)

        proc_group = QGroupBox("공정 및 조직")
        proc_group_layout = QVBoxLayout(proc_group)
        proc_group_layout.setContentsMargins(12, 12, 12, 12)
        proc_group_layout.setSpacing(12)

        proc_form = QFormLayout()
        proc_form.setContentsMargins(0, 0, 0, 0)
        proc_form.setHorizontalSpacing(14)
        proc_form.setVerticalSpacing(10)
        proc_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        solution_label = QLabel("고용화 열처리 온도 (K)")
        solution_field = QLineEdit("1323")
        proc_form.addRow(solution_label, solution_field)
        input_store["Solution_treatment_temperature"] = solution_field
        self._prediction_input_labels.append(solution_label)
        self._prediction_input_fields.append(solution_field)

        cooling_label = QLabel("냉각 방식")
        self.pretrained_cooling_combo = QComboBox()
        self.pretrained_cooling_combo.addItems(["로냉 (furnace)", "공냉 (air)", "수냉 (water)"])
        self.pretrained_cooling_combo.setCurrentIndex(2)
        self.pretrained_cooling_combo.currentIndexChanged.connect(self._sync_pretrained_cooling_inputs)
        proc_form.addRow(cooling_label, self.pretrained_cooling_combo)
        self._prediction_input_labels.append(cooling_label)

        water_field = QLineEdit("1")
        air_field = QLineEdit("0")
        water_field.hide()
        air_field.hide()
        input_store["Water_Quenched_after_s.t."] = water_field
        input_store["Air_Quenched_after_s.t."] = air_field

        ni_eq_label = QLabel("Ni 당량")
        ni_eq_field = QLineEdit("0.0")
        proc_form.addRow(ni_eq_label, ni_eq_field)
        input_store["Ni_eq"] = ni_eq_field
        self._prediction_input_labels.append(ni_eq_label)
        self._prediction_input_fields.append(ni_eq_field)

        cr_eq_label = QLabel("Cr 당량")
        cr_eq_field = QLineEdit("0.0")
        proc_form.addRow(cr_eq_label, cr_eq_field)
        input_store["Cr_eq"] = cr_eq_field
        self._prediction_input_labels.append(cr_eq_label)
        self._prediction_input_fields.append(cr_eq_field)

        proc_group_layout.addLayout(proc_form)
        parent_layout.addWidget(proc_group)
        self._prediction_input_groups.append(proc_group)

        extra_group = QGroupBox("추가 특성")
        extra_group_layout = QVBoxLayout(extra_group)
        extra_group_layout.setContentsMargins(12, 12, 12, 12)
        extra_group_layout.setSpacing(10)

        info_label = QLabel("위 입력과 겹치지 않는 공정 및 조직 관련 특성만 선택해서 추가할 수 있습니다.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 11px; color: #64748B;")
        extra_group_layout.addWidget(info_label)

        self._pretrained_extra_form_widget = QWidget()
        self._pretrained_extra_form_layout = QFormLayout(self._pretrained_extra_form_widget)
        self._pretrained_extra_form_layout.setContentsMargins(0, 0, 0, 0)
        self._pretrained_extra_form_layout.setHorizontalSpacing(14)
        self._pretrained_extra_form_layout.setVerticalSpacing(10)
        self._pretrained_extra_form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        extra_group_layout.addWidget(self._pretrained_extra_form_widget)

        self._add_feature_btn = QPushButton("추가 특성 선택")
        self._add_feature_btn.setFixedHeight(30)
        self._add_feature_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_feature_btn.clicked.connect(self._open_pretrained_add_feature_dialog)
        extra_group_layout.addWidget(self._add_feature_btn)

        parent_layout.addWidget(extra_group)
        self._prediction_input_groups.append(extra_group)
        self._sync_pretrained_cooling_inputs(self.pretrained_cooling_combo.currentIndex())
        self._refresh_pretrained_extra_feature_ui()

    def _sync_pretrained_cooling_inputs(self, index):
        water_value, air_value = ("0", "0")
        if index == 1:
            air_value = "1"
        elif index == 2:
            water_value = "1"

        for key, value in (
            ("Water_Quenched_after_s.t.", water_value),
            ("Air_Quenched_after_s.t.", air_value),
        ):
            field = getattr(self, "pretrained_inputs", {}).get(key)
            if field:
                self._set_prediction_field_value(field, value)

    def _get_pretrained_extra_feature_candidates(self):
        reserved = set(self._COMPOSITION_KEYS) | {
            "Solution_treatment_temperature",
            "Water_Quenched_after_s.t.",
            "Air_Quenched_after_s.t.",
            "Ni_eq",
            "Cr_eq",
        }
        return [name for name in self._PRETRAINED_EXTRA_FEATURE_ORDER if name not in reserved]

    def _open_pretrained_add_feature_dialog(self):
        available = self._get_pretrained_extra_feature_candidates()
        already = set(getattr(self, "_pretrained_extra_feature_names", []))

        dialog = QDialog(self)
        dialog.setWindowTitle("추가 특성 선택")
        dialog.setFixedSize(400, 480)
        dialog.setStyleSheet("background: #FFFFFF;")

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 헤더 ──────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background: #F8FAFC; border-bottom: 1px solid #E2E8F0;")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 16, 20, 14)
        hl.setSpacing(3)
        title_lbl = QLabel("추가 특성 선택")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #111827; background: transparent; border: none;")
        desc_lbl = QLabel("사전학습 예측에 사용할 추가 특성을 선택하세요.")
        desc_lbl.setStyleSheet("font-size: 11px; color: #64748B; background: transparent; border: none;")
        hl.addWidget(title_lbl)
        hl.addWidget(desc_lbl)
        main_layout.addWidget(header)

        # ── 스크롤 콘텐츠 ─────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: #FFFFFF; border: none;")

        content = QWidget()
        content.setStyleSheet("background: #FFFFFF;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(0)

        _GROUPS = [
            ("공정 조건", ["Solution_treatment_time(s)", "Type of melting", "Size of ingot", "Product form", "Temperature (K)"]),
            ("조직 특성", ["Grains mm-2"]),
            ("합금 지표", ["Ni_eq", "Cr_eq", "Cr_Ni_ratio", "C_plus_N"]),
        ]

        checks = {}

        def _sec_header(text):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #1B6AC9; "
                "background: transparent; border: none; padding: 0;"
            )
            lbl.setFixedHeight(20)
            rl.addWidget(lbl)
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("border: none; border-top: 1px solid #CBD5E1; background: transparent;")
            line.setFixedHeight(1)
            rl.addWidget(line, 1)
            return row

        cb_style = (
            "QCheckBox { font-size: 12px; color: #1E293B; background: transparent; "
            "padding: 5px 0 5px 4px; spacing: 8px; }"
            "QCheckBox::indicator { width: 15px; height: 15px; border-radius: 3px; "
            "border: 1px solid #94A3B8; background: #FFFFFF; }"
            "QCheckBox::indicator:checked { background: #1E293B; border-color: #1E293B; image: none; }"
            "QCheckBox::indicator:hover { border-color: #1E293B; }"
        )

        first = True
        for group_name, keys in _GROUPS:
            group_keys = [k for k in keys if k in available]
            if not group_keys:
                continue
            if not first:
                cl.addSpacing(14)
            first = False
            cl.addWidget(_sec_header(group_name))
            cl.addSpacing(6)
            for key in group_keys:
                label = self._PRETRAINED_EXTRA_FEATURE_LABELS.get(key, key)
                cb = QCheckBox(label)
                cb.setChecked(key in already)
                cb.setStyleSheet(cb_style)
                checks[key] = cb
                cl.addWidget(cb)

        cl.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        # ── 하단 버튼 바 ──────────────────────────────────
        btn_bar = QWidget()
        btn_bar.setStyleSheet("background: #F8FAFC; border-top: 1px solid #E2E8F0;")
        bl = QHBoxLayout(btn_bar)
        bl.setContentsMargins(16, 10, 16, 10)
        bl.setSpacing(8)
        bl.addStretch()
        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(72, 32)
        cancel_btn.setStyleSheet(
            "QPushButton { background: #FFFFFF; color: #374151; border: 1px solid #D1D5DB; "
            "border-radius: 6px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: #F3F4F6; }"
        )
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("확인")
        ok_btn.setFixedSize(72, 32)
        ok_btn.setStyleSheet(
            "QPushButton { background: #1E293B; color: white; border: none; "
            "border-radius: 6px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: #334155; }"
        )
        ok_btn.clicked.connect(dialog.accept)
        bl.addWidget(cancel_btn)
        bl.addWidget(ok_btn)
        main_layout.addWidget(btn_bar)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._pretrained_extra_feature_names = [
                key for key in available
                if key in checks and checks[key].isChecked()
            ]
            self._refresh_pretrained_extra_feature_ui()

    def _refresh_pretrained_extra_feature_ui(self):
        input_store = getattr(self, "pretrained_inputs", {})
        for name in list(getattr(self, "_pretrained_extra_feature_widgets", {})):
            input_store.pop(name, None)

        self._discard_prediction_widgets(
            getattr(self, "_pretrained_extra_feature_labels", []),
            getattr(self, "_pretrained_extra_feature_fields", []),
        )

        while self._pretrained_extra_form_layout.rowCount() > 0:
            self._pretrained_extra_form_layout.removeRow(0)

        self._pretrained_extra_feature_widgets = {}
        self._pretrained_extra_feature_labels = []
        self._pretrained_extra_feature_fields = []

        for name in getattr(self, "_pretrained_extra_feature_names", []):
            label = QLabel(self._PRETRAINED_EXTRA_FEATURE_LABELS.get(name, name))
            field = QLineEdit(self._PRETRAINED_EXTRA_FEATURE_DEFAULTS.get(name, "0"))
            if name in self._PRETRAINED_CALCULATED_FEATURES:
                self._register_readonly_field(field)

            remove_btn = QPushButton("X")
            remove_btn.setFixedSize(26, 26)
            remove_btn.setStyleSheet(
                "QPushButton { background: #FEE2E2; color: #DC2626; border: none; "
                "border-radius: 4px; font-weight: 700; }"
                "QPushButton:hover { background: #FECACA; }"
            )
            remove_btn.clicked.connect(lambda _checked=False, feature=name: self._remove_pretrained_extra_feature(feature))

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            row_layout.addWidget(field, 1)
            row_layout.addWidget(remove_btn)

            self._pretrained_extra_form_layout.addRow(label, row_widget)
            input_store[name] = field
            self._pretrained_extra_feature_widgets[name] = field
            self._pretrained_extra_feature_labels.append(label)
            self._pretrained_extra_feature_fields.append(field)
            self._prediction_input_labels.append(label)
            self._prediction_input_fields.append(field)

        self._apply_prediction_input_styles()
        self._update_composition_derived_fields(input_store)

    def _remove_pretrained_extra_feature(self, feature_name):
        self._pretrained_extra_feature_names = [
            name for name in getattr(self, "_pretrained_extra_feature_names", []) if name != feature_name
        ]
        self._refresh_pretrained_extra_feature_ui()

    def _show_prediction_guide(self, _page):
        steps = [
            {
                "widget": self.pretrained_inputs.get(
                    list(self.pretrained_inputs.keys())[0]
                ).parent().parent().parent().parent()
                if self.pretrained_inputs else None,
                "text": "① 합금 조성 입력\n\n각 원소의 wt% 값을 입력하세요.\nFe는 보통 96% 이상, 나머지는 소량.\n\n기본값은 오스테나이트계 스테인리스강 기준입니다.",
            },
            {
                "widget": self.pretrained_predict_btn,
                "text": "② 예측 실행\n\n버튼 클릭 시 미리 정의된\n사전학습 모델로 물성을 예측합니다.\n\n평균값과 불확실도를 함께 제공합니다.",
            },
            {
                "widget": self.pretrained_result_tabs,
                "text": "③ 예측 결과 탭\n\nYield Stress / UTS / 연신율 /\n단면감소율 예측값을 확인합니다.\n\n오차 범위가 좁을수록 신뢰도가 높습니다.",
                "on_show": lambda: self.pretrained_result_tabs.setCurrentIndex(0),
            },
            {
                "widget": self.pretrained_result_tabs,
                "text": "④ Stress-Strain Curve 탭\n\n예측 물성 기반 응력-변형률 곡선.\n• 초록: 탄성 구간 (복원 가능)\n• 주황: 소성 구간 (영구 변형)\n• 빨강: 네킹→파단 구간",
                "on_show": lambda: self.pretrained_result_tabs.setCurrentIndex(1),
            },
            {
                "widget": getattr(self, "_pretrained_explore_btn", None),
                "text": "⑤ 자세하게 보기\n\n예측 후 활성화되는 버튼입니다.\n\n표점거리·폭·두께를 입력하면\n변형률에 따른 응력 변화를\n단계별로 시뮬레이션할 수 있습니다.\n\n항복점·UTS·파단점이\n곡선 위에 실시간으로 표시됩니다.",
                "on_show": lambda: self.pretrained_result_tabs.setCurrentIndex(1),
            },
        ]
        if not self.pretrained_inputs:
            steps[0]["widget"] = None
        else:
            try:
                first_key = list(self.pretrained_inputs.keys())[0]
                le = self.pretrained_inputs[first_key]
                steps[0]["widget"] = le.parent().parent().parent().parent()
            except Exception:
                steps[0]["widget"] = None

        cw = self.centralWidget()
        toolbar_h = self._toolbar_widget.height()
        overlay = PredictionGuideOverlay(steps, parent=cw, toolbar_h=toolbar_h)
        overlay.raise_()
        overlay.show()

    def _build_prediction_input_sections(self, parent_layout, input_store):
        comp_group = QGroupBox("합금 조성 (wt%)")
        comp_group_layout = QVBoxLayout(comp_group)
        comp_group_layout.setContentsMargins(12, 12, 12, 12)
        comp_group_layout.setSpacing(12)
        composition_defaults = {
            "Fe": "96.0",
            "C": "0.08",
            "Si": "0.4",
            "Mn": "1.5",
            "P": "0.01",
            "S": "0.005",
            "Ni": "0.2",
            "Cr": "0.3",
            "Mo": "0.05",
            "Cu": "0.1",
            "V": "0.01",
            "N": "0.005",
            "Nb": "0.02",
            "Ti": "0.01",
            "B": "0.0005",
            "Al": "0.03",
        }
        composition_items = list(composition_defaults.items())
        midpoint = (len(composition_items) + 1) // 2
        comp_columns = QHBoxLayout()
        comp_columns.setContentsMargins(0, 0, 0, 0)
        comp_columns.setSpacing(16)
        comp_columns.addLayout(self._create_prediction_form(composition_items[:midpoint], input_store))
        comp_columns.addLayout(self._create_prediction_form(composition_items[midpoint:], input_store))
        comp_group_layout.addLayout(comp_columns)
        parent_layout.addWidget(comp_group)
        self._prediction_input_groups.append(comp_group)

        proc_group = QGroupBox("공정 및 조직")
        proc_group_layout = QVBoxLayout(proc_group)
        proc_group_layout.setContentsMargins(12, 12, 12, 12)
        proc_group_layout.setSpacing(12)
        proc_defaults = {
            "Solution_treatment_temperature": "1050",
            "Solution_treatment_time(s)": "3600",
            "Water_Quenched_after_s.t.": "1",
            "Air_Quenched_after_s.t.": "0",
            "Grains mm-2": "500",
            "Type of melting": "2",
            "Size of ingot": "50",
            "Product form": "3",
            "Temperature (K)": "300",
        }
        proc_group_layout.addLayout(self._create_prediction_form(list(proc_defaults.items()), input_store))
        parent_layout.addWidget(proc_group)
        self._prediction_input_groups.append(proc_group)
        self._apply_prediction_input_styles()

    def _create_prediction_form(self, items, input_store):
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for col, value in items:
            label = QLabel(col)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            line_edit = QLineEdit()
            line_edit.setText(value)
            line_edit.deselect()
            line_edit.setCursorPosition(0)
            form_layout.addRow(label, line_edit)
            input_store[col] = line_edit
            self._prediction_input_labels.append(label)
            self._prediction_input_fields.append(line_edit)
        return form_layout

    def _apply_prediction_input_styles(self):
        c = self._theme()
        group_style = (
            "QGroupBox { "
            f"background: {c['panel_bg']}; border: 1px solid {c['border']}; border-radius: 12px; "
            "margin-top: 10px; padding-top: 14px; font-weight: 700; }"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {c['text_primary']}; }}"
        )
        line_edit_style = (
            "QLineEdit { "
            f"background: {c['input_bg']}; color: {c['text_primary']}; border: 1px solid {c['border']}; "
            "border-radius: 8px; padding: 7px 10px; selection-background-color: #1E293B; selection-color: #FFFFFF; }"
            "QLineEdit:focus { border-color: #1E293B; }"
        )
        for group in self._prediction_input_groups:
            group.setStyleSheet(group_style)
        label_color = "#555555" if not self._dark_mode else c['text_sec']
        for label in self._prediction_input_labels:
            label.setStyleSheet(
                f"color: {label_color}; font-size: 12px; font-weight: 600; "
                "padding-right: 4px; background: transparent;"
            )
        for field in self._prediction_input_fields:
            field.setStyleSheet(line_edit_style)
        if hasattr(self, "_fe_readonly_fields"):
            for fe_field in self._fe_readonly_fields:
                self._apply_fe_readonly_style(fe_field)
        if hasattr(self, "_pretrained_reset_btn"):
            self._pretrained_reset_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {c['text_label']}; "
                f"border: 1px solid {c['border']}; border-radius: 6px; "
                "font-size: 11px; font-weight: 600; padding: 0 10px; }"
                f"QPushButton:hover {{ background: {c['muted_bg']}; color: {c['text_sec']}; }}"
            )
        if hasattr(self, "_add_feature_btn"):
            self._add_feature_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {c['text_label']}; "
                f"border: 1px solid {c['border']}; border-radius: 8px; "
                "font-size: 11px; font-weight: 600; padding: 0 10px; }"
                f"QPushButton:hover {{ background: {c['muted_bg']}; color: {c['text_sec']}; }}"
            )

    def _apply_fe_readonly_style(self, field):
        if self._dark_mode:
            bg, color, border = "#1E2229", "#64748B", "#3A4048"
        else:
            bg, color, border = "#F1F5F9", "#64748B", "#CBD5E1"
        field.setStyleSheet(
            f"QLineEdit {{ background: {bg}; color: {color}; border: 1px solid {border}; "
            "border-radius: 8px; padding: 7px 10px; }"
            f"QLineEdit:focus {{ border-color: {border}; }}"
        )

    def _setup_fe_auto_update(self, input_store):
        fe_field = input_store.get("Fe")
        if not fe_field:
            return
        self._register_readonly_field(fe_field)

        other_keys = [k for k in self._COMPOSITION_KEYS if k != "Fe" and k in input_store]

        def _update_fe():
            self._update_composition_derived_fields(input_store)

        for key in other_keys:
            input_store[key].textChanged.connect(_update_fe)
        _update_fe()

    def _register_readonly_field(self, field):
        field.setReadOnly(True)
        if not hasattr(self, "_fe_readonly_fields"):
            self._fe_readonly_fields = []
        if field not in self._fe_readonly_fields:
            self._fe_readonly_fields.append(field)
        self._apply_fe_readonly_style(field)

    def _discard_prediction_widgets(self, labels, fields):
        for label in labels:
            if label in self._prediction_input_labels:
                self._prediction_input_labels.remove(label)
        for field in fields:
            if field in self._prediction_input_fields:
                self._prediction_input_fields.remove(field)
        if hasattr(self, "_fe_readonly_fields"):
            self._fe_readonly_fields = [field for field in self._fe_readonly_fields if field not in fields]

    def _format_prediction_number(self, value):
        text = f"{float(value):.4f}".rstrip("0").rstrip(".")
        return text or "0"

    def _set_prediction_field_value(self, field, value):
        if field is None:
            return
        field.blockSignals(True)
        field.setText(str(value))
        field.blockSignals(False)

    def _update_composition_derived_fields(self, input_store):
        def _value(key):
            widget = input_store.get(key)
            if widget is None:
                return 0.0
            try:
                return float(widget.text())
            except ValueError:
                return 0.0

        total = sum(_value(key) for key in self._COMPOSITION_KEYS if key != "Fe" and key in input_store)
        self._set_prediction_field_value(
            input_store.get("Fe"),
            self._format_prediction_number(100.0 - total),
        )

        ni = _value("Ni")
        cr = _value("Cr")
        c = _value("C")
        n = _value("N")
        mn = _value("Mn")
        mo = _value("Mo")
        si = _value("Si")
        nb = _value("Nb")
        cu = _value("Cu")

        derived_values = {
            "Ni_eq": ni + (30.0 * c) + (0.5 * mn) + (30.0 * n) + (0.3 * cu),
            "Cr_eq": cr + mo + (1.5 * si) + (0.5 * nb),
            "Cr_Ni_ratio": (cr / ni) if abs(ni) > 1e-8 else 0.0,
            "C_plus_N": c + n,
        }
        for key, value in derived_values.items():
            field = input_store.get(key)
            if field is None:
                continue
            self._register_readonly_field(field)
            self._set_prediction_field_value(field, self._format_prediction_number(value))

    def _reposition_floating_chatbot(self):
        if not hasattr(self, "_floating_chatbot"):
            return
        icon = self._floating_chatbot
        geo = self.frameGeometry()
        pad = 16

        if not self._floating_chatbot_placed:
            # 최초 1회: 우하단 고정
            icon.move(geo.right() - icon.width() - pad, geo.bottom() - icon.height() - pad)
            self._floating_chatbot_placed = True
            return

        # 창 이동/리사이즈 후 경계 밖으로 벗어난 경우만 안으로 당김
        cur = icon.pos()
        x = max(geo.left() + pad, min(cur.x(), geo.right()  - icon.width()  - pad))
        y = max(geo.top()  + pad, min(cur.y(), geo.bottom() - icon.height() - pad))
        if x != cur.x() or y != cur.y():
            icon.move(x, y)

    def resizeEvent(self, event):
        from PyQt6.QtWidgets import QMainWindow
        QMainWindow.resizeEvent(self, event)
        self._reposition_floating_chatbot()

    def moveEvent(self, event):
        from PyQt6.QtWidgets import QMainWindow
        QMainWindow.moveEvent(self, event)
        if hasattr(self, "_floating_chatbot") and self._floating_chatbot_placed:
            dx = event.pos().x() - event.oldPos().x()
            dy = event.pos().y() - event.oldPos().y()
            icon = self._floating_chatbot
            icon.move(icon.pos().x() + dx, icon.pos().y() + dy)

    def _set_floating_visible(self, visible: bool):
        if hasattr(self, "_floating_chatbot"):
            if visible:
                self._floating_chatbot.show()
            else:
                self._floating_chatbot.hide()
        if not visible and hasattr(self, "_llm_chat_dialog") and self._llm_chat_dialog is not None:
            self._llm_chat_dialog.hide()

    def closeEvent(self, event):
        self._set_floating_visible(False)
        event.accept()

    def hideEvent(self, event):
        self._set_floating_visible(False)
        from PyQt6.QtWidgets import QMainWindow
        QMainWindow.hideEvent(self, event)

    def showEvent(self, event):
        from PyQt6.QtWidgets import QMainWindow
        QMainWindow.showEvent(self, event)
        self._set_floating_visible(True)

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QMainWindow
        QMainWindow.changeEvent(self, event)
        if event.type() == QEvent.Type.WindowStateChange:
            minimized = bool(self.windowState() & Qt.WindowState.WindowMinimized)
            self._set_floating_visible(not minimized)

    def show_quality_help(self):
        help_text = """
        <h2>데이터 전처리 도움말</h2>
        <p>전처리 탭에서는 누락값, 이상치, 형식 오류, 도메인 범위를 학습 전에 먼저 정리합니다.</p>
        <h3>권장 순서</h3>
        <p>파일 선택 → 도메인 기준 설정 → 데이터 품질 처리 설정 → 전처리 실행 → 합금 지표 생성 → 결과 확인</p>
        <h3>추천 시작값</h3>
        <p>누락값 처리: <b>중앙값으로 채우기(med)</b><br>이상치 처리: <b>감지 범위로 보정(iqr)</b><br>형식 검증: <b>잘못된 값을 NaN으로 변환(nan)</b><br>이상치 민감도: <b>1.5</b></p>
        <h3>합금 지표 설명</h3>
        <p><b>Ni 당량 (Ni_eq)</b>: 오스테나이트 안정성을 보는 지표입니다.<br><b>Cr 당량 (Cr_eq)</b>: 페라이트 형성 경향을 보는 지표입니다.<br><b>Cr/Ni 비율</b>: 조직 균형을 보는 지표입니다.<br><b>침입형 원소 합 (C+N)</b>: 고용강화와 고온 강도에 영향을 주는 지표입니다.</p>
        <h3>결과 확인</h3>
        <p>전처리 또는 합금 지표 생성이 끝나면 오른쪽 표에서 전체 데이터를 바로 확인할 수 있습니다.</p>
        """
        self.show_help_dialog("전처리 도움말", help_text)

    def show_model_training_help(self):
        help_text = """
        <p style="font-size:13px; color:#374151;">
        전처리 완료 후 이 탭에서 모델을 학습합니다.
        모델은 4가지 제공되며 결과 R²로 비교하면 됩니다.
        </p>

        <p style="margin-top:14px; font-size:12px; color:#374151;">
        <b>RF</b> — 데이터 적을 때 무난. 처음엔 이걸로 시작.<br>
        <b>GBM</b> — RF랑 비교용으로 돌려보기 좋음.<br>
        <b>MLP</b> — 데이터 많으면 써볼 만함 (300행↑ 권장).<br>
        <b>TFP</b> — 예측값에 불확실성 범위까지 같이 보고 싶을 때.
        </p>

        <p style="margin-top:14px; font-size:12px; color:#374151;">
        <b>학습 컬럼 선택</b> 탭에서 입력 변수를 골라서 씁니다.<br>
        체크 안 된 컬럼은 학습·예측 모두 제외됩니다.
        </p>

        <p style="margin-top:14px; font-size:11px; color:#6B7280;">
        전처리 설정 바꿨으면 전처리부터 다시 돌리고 학습할 것.
        </p>
        """
        self.show_help_dialog("모델 학습", help_text)

    def _reset_pretrained_inputs(self):
        """합금 조성 및 공정 입력값을 기본값으로 초기화한다."""
        composition_defaults = {
            "C": "0.08", "Si": "0.4", "Mn": "1.5", "P": "0.01",
            "S": "0.005", "Ni": "0.2", "Cr": "0.3", "Mo": "0.05",
            "Cu": "0.1", "V": "0.01", "N": "0.005", "Nb": "0.02",
            "Ti": "0.01", "B": "0.0005", "Al": "0.03",
            "Solution_treatment_temperature": "1323",
        }
        for key, value in composition_defaults.items():
            field = self.pretrained_inputs.get(key)
            if field and not field.isReadOnly():
                self._set_prediction_field_value(field, value)
        if hasattr(self, "pretrained_cooling_combo"):
            self.pretrained_cooling_combo.setCurrentIndex(2)
        self._update_composition_derived_fields(self.pretrained_inputs)

    def show_help_dialog(self, title, html_text):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(820, 640)

        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        browser.setStyleSheet("QTextBrowser { font-size: 15px; line-height: 1.7; padding: 16px; }")
        browser.setHtml(html_text)
        layout.addWidget(browser)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(dialog.accept)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        dialog.exec()
